from flask import Flask, request

import anthropic

app = Flask(__name__)
client = anthropic.Anthropic(api_key="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")

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

@app.route("/checkmate", methods=["POST"])
def checkmate():
    datos = request.json
    mensaje = datos.get("mensaje", "")
    historial = datos.get("historial", [])
    
    historial.append({"role": "user", "content": mensaje})
    
    respuesta = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        system=system,
        messages=historial
    )
    
    respuesta_checkmate = respuesta.content[0].text
    historial.append({"role": "assistant", "content": respuesta_checkmate})
    
    return {"respuesta": respuesta_checkmate, "historial": historial}

if __name__ == "__main__":
    app.run(debug=True)