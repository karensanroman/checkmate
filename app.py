from flask import Flask, request
import anthropic
import os
import requests
import base64
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
        contenido_mensaje.append({
            "type": "text",
            "text": mensaje_entrante
        })
    elif num_media > 0:
        contenido_mensaje.append({
            "type": "text",
            "text": "Analiza este producto y dime qué tan confiable es su consumo."
        })

    historial_usuarios[numero_usuario].append({
        "role": "user",
        "content": contenido_mensaje
    })

    respuesta = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        system=system,
        messages=historial_usuarios[numero_usuario]
    )

    mensaje_checkmate = respuesta.content[0].text

    historial_usuarios[numero_usuario].append({
        "role": "assistant",
        "content": mensaje_checkmate
    })

    resp = MessagingResponse()
    resp.message(mensaje_checkmate)
    return str(resp)

if __name__ == "__main__":
    app.run(debug=True)