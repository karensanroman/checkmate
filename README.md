# Checkmate 🤖

Agente de IA que verifica si un remedio, suplemento o medicamento tiene respaldo científico real. Disponible vía WhatsApp.

## ¿Qué hace?

- Analiza suplementos y medicamentos por nombre o foto
- Consulta estudios científicos reales en PubMed en tiempo real
- Verifica datos oficiales en OpenFDA
- Responde con evidencia, no con opiniones
- Tono casual pero confiable — como un amigo que sabe, no un robot

## Stack técnico

- **Claude API (Anthropic)** — modelo de lenguaje y visión
- **Flask** — servidor web en Python
- **Twilio** — integración con WhatsApp
- **Railway** — deploy en la nube
- **PubMed API** — estudios científicos
- **OpenFDA API** — datos oficiales de medicamentos

## Arquitectura
Usuario (WhatsApp) → Twilio → Flask (Railway) → Claude API

↓

PubMed / OpenFDA

## Cómo funciona

1. Usuario manda texto o imagen por WhatsApp
2. Twilio recibe el mensaje y lo manda al servidor
3. El servidor descarga la imagen (si hay) y la convierte a base64
4. Claude analiza el contenido y decide si consultar PubMed u OpenFDA
5. Claude combina la evidencia y responde al usuario

## Lo que aprendí construyendo esto

- Cómo funciona tool use en la API de Anthropic
- La diferencia entre un chatbot y un agente real
- Variables de entorno para proteger credenciales
- Deploy con Railway y GitHub
- Integración de APIs externas en un agente

## Autora

Karen San Roman — Engineering Data Analyst & AI Developer  
[LinkedIn](https://linkedin.com/in/karensanroman)