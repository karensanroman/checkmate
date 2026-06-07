from flask import Flask, request
import anthropic
import os
import requests
import base64
import json
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

system = """Eres Checkmate, un asistente que verifica si remedios, suplementos o medicamentos tienen respaldo científico real.
Tu tono: casual pero confiable. Como ese amigo que estudió medicina o nutrición y te habla sin rollos, pero tampoco te dice tonterías. Directo, honesto, sin alarmismo.
Reglas:
- Nunca diagnosticas ni recetas
- Si algo no tiene evidencia, lo dices claro pero sin drama
- Si algo sí funciona, tampoco exageras
- En todas tus respuestas siempre recomiendas consultar a un médico para decisiones importantes
- Máximo 5 líneas por respuesta
- Si el usuario quiere profundizar, pregunta en qué parte
Tu respuesta debe de contener:
1. Un respaldo de evidencia científica del consumo del producto, porcentaje de confiabilidad de su consumo.
2. Lo que dicen los estudios (a favor y/o limitaciones)
3. Conclusión práctica
4. Si aplica, cuándo sí vale la pena consumirlo y cuándo no"""


herramientas = [
    {
        "name": "buscar_pubmed",
        "description": "Busca estudios científicos reales en PubMed sobre un ingrediente, suplemento o medicamento. Úsala siempre para respaldar tu análisis con evidencia actual.",
        "input_schema": {
            "type": "object",
            "properties": {
                "termino": {
                    "type": "string",
                    "description": "El ingrediente o medicamento a buscar en inglés, ejemplo: magnesium sleep"
                }
            },
            "required": ["termino"]
        }
    },
    {
        "name": "buscar_openfda",
        "description": "Busca información oficial de la FDA sobre medicamentos: efectos adversos, alertas de seguridad, contraindicaciones. Úsala para medicamentos específicos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "medicamento": {
                    "type": "string",
                    "description": "El nombre del medicamento a buscar, ejemplo: ibuprofen"
                }
            },
            "required": ["medicamento"]
        }
    }
]

def buscar_pubmed(termino):
    try:
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={termino}&retmax=3&retmode=json"
        ids = requests.get(url).json()["esearchresult"]["idlist"]
        if not ids:
            return "No se encontraron estudios."
        ids_str = ",".join(ids)
        url_resumen = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={ids_str}&retmode=json"
        data = requests.get(url_resumen).json()
        estudios = []
        for id in ids:
            titulo = data["result"][id].get("title", "Sin título")
            año = data["result"][id].get("pubdate", "")[:4]
            estudios.append(f"- {titulo} ({año})")
        return "\n".join(estudios)
    except:
        return "Error consultando PubMed."

def buscar_openfda(medicamento):
    try:
        url = f"https://api.fda.gov/drug/label.json?search=openfda.brand_name:{medicamento}&limit=1"
        data = requests.get(url).json()
        if "results" not in data:
            return "No se encontró información en FDA."
        resultado = data["results"][0]
        info = []
        if "warnings" in resultado:
            info.append("Advertencias: " + resultado["warnings"][0][:300])
        if "adverse_reactions" in resultado:
            info.append("Efectos adversos: " + resultado["adverse_reactions"][0][:300])
        if "contraindications" in resultado:
            info.append("Contraindicaciones: " + resultado["contraindications"][0][:300])
        return "\n".join(info) if info else "Sin advertencias registradas."
    except:
        return "Error consultando OpenFDA."

def ejecutar_herramienta(nombre, parametros):
    if nombre == "buscar_pubmed":
        return buscar_pubmed(parametros["termino"])
    elif nombre == "buscar_openfda":
        return buscar_openfda(parametros["medicamento"])
    return "Herramienta no encontrada."

historial_usuarios = {}

def descargar_imagen_base64(url, twilio_sid, twilio_token):
    respuesta = requests.get(url, auth=(twilio_sid, twilio_token))
    tipo = respuesta.headers.get("Content-Type", "image/jpeg")
    imagen_base64 = base64.b64encode(respuesta.content).decode("utf-8")
    return imagen_base64, tipo

@app.route("/checkmate", methods=["POST"])
def checkmate():
    mensaje_entrante = request.form.get("Body", "").strip()
    numero_usuario = request.form.get("From", "")
    num_media = int(request.form.get("NumMedia", 0))

    twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")

    if numero_usuario not in historial_usuarios:
        historial_usuarios[numero_usuario] = []

    contenido_mensaje = []

    if num_media > 0:
        url_imagen = request.form.get("MediaUrl0", "")
        imagen_base64, tipo_imagen = descargar_imagen_base64(url_imagen, twilio_sid, twilio_token)
        contenido_mensaje.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": tipo_imagen,
                "data": imagen_base64
            }
        })

    if mensaje_entrante:
        contenido_mensaje.append({"type": "text", "text": mensaje_entrante})
    elif num_media > 0:
        contenido_mensaje.append({"type": "text", "text": "Analiza este producto y dime qué tan confiable es su consumo."})

    historial_usuarios[numero_usuario].append({
        "role": "user",
        "content": contenido_mensaje
    })

    # Loop de agente
    while True:
        respuesta = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system=system,
            tools=herramientas,
            messages=historial_usuarios[numero_usuario]
        )

        if respuesta.stop_reason == "end_turn":
            mensaje_checkmate = respuesta.content[0].text
            break

        if respuesta.stop_reason == "tool_use":
            historial_usuarios[numero_usuario].append({
                "role": "assistant",
                "content": respuesta.content
            })

            resultados_herramientas = []
            for bloque in respuesta.content:
                if bloque.type == "tool_use":
                    resultado = ejecutar_herramienta(bloque.name, bloque.input)
                    resultados_herramientas.append({
                        "type": "tool_result",
                        "tool_use_id": bloque.id,
                        "content": resultado
                    })

            historial_usuarios[numero_usuario].append({
                "role": "user",
                "content": resultados_herramientas
            })

    historial_usuarios[numero_usuario].append({
        "role": "assistant",
        "content": mensaje_checkmate
    })

    resp = MessagingResponse()
    resp.message(mensaje_checkmate)
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)