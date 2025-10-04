from flask import Flask, render_template, request, jsonify, redirect, url_for
from openai import OpenAI
import requests
import base64
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

app = Flask(__name__)

# Cargar credenciales desde variables de entorno
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ==== CONFIG PAYPAL ====
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")
PAYPAL_API_BASE = os.getenv("PAYPAL_API_BASE")

# Validar que las credenciales se cargaron correctamente
if not all([PAYPAL_CLIENT_ID, PAYPAL_SECRET, PAYPAL_API_BASE]):
    raise ValueError("Faltan credenciales de PayPal en el archivo .env")

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("Falta la clave de OpenAI en el archivo .env")

# === Obtener token de PayPal ===
def get_paypal_token():
    try:
        auth = base64.b64encode(f"{PAYPAL_CLIENT_ID}:{PAYPAL_SECRET}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"grant_type": "client_credentials"}
        
        r = requests.post(f"{PAYPAL_API_BASE}/v1/oauth2/token", headers=headers, data=data)
        
        print(f"Status Code Token: {r.status_code}")
        print(f"Response Token: {r.text}")
        
        if r.status_code == 200:
            return r.json().get("access_token")
        else:
            print(f"❌ Error obteniendo token: {r.text}")
            return None
    except Exception as e:
        print(f"❌ Excepción en get_paypal_token: {str(e)}")
        return None

@app.route("/test_credenciales")
def test_credenciales():
    try:
        token = get_paypal_token()
        if token:
            return jsonify({
                "success": True,
                "mensaje": "✅ Credenciales de PayPal válidas",
                "token_obtenido": "Token válido",
                "client_id_usado": PAYPAL_CLIENT_ID[:20] + "...",
                "siguiente_paso": "Accede a /crear_producto para crear tu producto"
            })
        else:
            return jsonify({
                "success": False,
                "mensaje": "❌ No se pudo obtener el token",
                "verifica": "Client ID y Secret en las variables"
            }), 401
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# === PASO 1: Crear Producto (ejecuta solo una vez) ===
@app.route("/crear_producto", methods=["GET"])
def crear_producto():
    try:
        token = get_paypal_token()
        if not token:
            return jsonify({
                "success": False,
                "error": "No se pudo obtener token de PayPal",
                "mensaje": "Verifica tus credenciales en /test_credenciales"
            }), 401
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "name": "Chat Poético IA - Suscripción Mensual",
            "description": "Acceso ilimitado al generador de poemas con IA",
            "type": "SERVICE",
            "category": "SOFTWARE"
        }
        
        print(f"📤 Enviando petición para crear producto...")
        r = requests.post(f"{PAYPAL_API_BASE}/v1/catalogs/products", headers=headers, json=data)
        
        print(f"Status Code Producto: {r.status_code}")
        print(f"Response Producto: {r.text}")
        
        if r.status_code == 201:
            producto = r.json()
            product_id = producto.get("id")
            return jsonify({
                "success": True,
                "mensaje": "✅ Producto creado exitosamente",
                "product_id": product_id,
                "nombre": producto.get("name"),
                "siguiente_paso": f"Ahora accede a: /crear_plan/{product_id}",
                "respuesta_completa": producto
            })
        else:
            return jsonify({
                "success": False,
                "error": "Error al crear producto",
                "status_code": r.status_code,
                "detalles": r.text
            }), r.status_code
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# === PASO 2: Crear Plan de Suscripción (ejecuta solo una vez) ===
@app.route("/crear_plan/<product_id>", methods=["GET"])
def crear_plan(product_id):
    try:
        token = get_paypal_token()
        if not token:
            return jsonify({
                "success": False,
                "error": "No se pudo obtener token de PayPal"
            }), 401
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        plan_data = {
            "product_id": product_id,
            "name": "Plan Mensual Chat Poético",
            "description": "Suscripción mensual de $25 USD",
            "status": "ACTIVE",
            "billing_cycles": [
                {
                    "frequency": {
                        "interval_unit": "MONTH",
                        "interval_count": 1
                    },
                    "tenure_type": "REGULAR",
                    "sequence": 1,
                    "total_cycles": 0,
                    "pricing_scheme": {
                        "fixed_price": {
                            "value": "25.00",
                            "currency_code": "USD"
                        }
                    }
                }
            ],
            "payment_preferences": {
                "auto_bill_outstanding": True,
                "setup_fee": {
                    "value": "0.00",
                    "currency_code": "USD"
                },
                "setup_fee_failure_action": "CONTINUE",
                "payment_failure_threshold": 3
            },
            "taxes": {
                "percentage": "0",
                "inclusive": False
            }
        }
        
        print(f"📤 Creando plan para producto: {product_id}")
        r = requests.post(f"{PAYPAL_API_BASE}/v1/billing/plans", headers=headers, json=plan_data)
        
        print(f"Status Code Plan: {r.status_code}")
        print(f"Response Plan: {r.text}")
        
        if r.status_code == 201:
            plan_info = r.json()
            plan_id = plan_info.get("id")
            return jsonify({
                "success": True,
                "mensaje": "✅ Plan creado exitosamente",
                "plan_id": plan_id,
                "status": plan_info.get("status"),
                "instruccion": f"Copia este PLAN_ID y reemplázalo en index.html: {plan_id}",
                "respuesta_completa": plan_info
            })
        else:
            return jsonify({
                "success": False,
                "error": "Error al crear plan",
                "status_code": r.status_code,
                "detalles": r.text
            }), r.status_code
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# === Ruta principal ===
@app.route("/")
def index():
    return render_template("index.html", paypal_client_id=PAYPAL_CLIENT_ID)

# === Ruta del chat ===
@app.route("/generar", methods=["POST"])
def generar():
    data = request.json
    mensaje_usuario = data.get("mensaje", "")
    
    try:
        respuesta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Eres un poeta que escribe poemas románticos con emojis."},
                {"role": "user", "content": f"Genera un poema {mensaje_usuario}"}
            ],
            max_tokens=400,
            temperature=0.9
        )

        poema = respuesta.choices[0].message.content.strip()
        return jsonify({"respuesta": poema})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Validar suscripción después del pago ===
@app.route("/validar_pago", methods=["POST"])
def validar_pago():
    data = request.json
    subscription_id = data.get("subscriptionID")
    
    token = get_paypal_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    r = requests.get(f"{PAYPAL_API_BASE}/v1/billing/subscriptions/{subscription_id}", headers=headers)
    subscription_data = r.json()
    
    return jsonify({
        "status": subscription_data.get("status"),
        "subscription_id": subscription_id,
        "subscriber_email": subscription_data.get("subscriber", {}).get("email_address")
    })

# === Cancelar suscripción ===
@app.route("/cancelar_suscripcion", methods=["POST"])
def cancelar_suscripcion():
    data = request.json
    subscription_id = data.get("subscription_id")
    
    token = get_paypal_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    cancel_data = {"reason": "Usuario solicitó cancelación"}
    
    r = requests.post(
        f"{PAYPAL_API_BASE}/v1/billing/subscriptions/{subscription_id}/cancel",
        headers=headers,
        json=cancel_data
    )
    
    if r.status_code == 204:
        return jsonify({"message": "Suscripción cancelada exitosamente"})
    else:
        return jsonify({"error": "No se pudo cancelar la suscripción"}), 400

@app.route("/pago_exitoso")
def pago_exitoso():
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Pago Exitoso</title>
        <style>
            body { font-family: Arial; text-align: center; padding: 50px; background: #ffe6f0; }
            .success { background: white; padding: 40px; border-radius: 15px; max-width: 500px; margin: 0 auto; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
            .success h1 { color: #28a745; }
            a { display: inline-block; margin-top: 20px; padding: 12px 24px; background: #d63384; color: white; text-decoration: none; border-radius: 8px; }
            a:hover { background: #a32461; }
        </style>
    </head>
    <body>
        <div class="success">
            <h1>✅ Suscripción Activada</h1>
            <p>¡Gracias por suscribirte al Chat de Poemas IA!</p>
            <p>Tu suscripción mensual de $25 USD está activa.</p>
            <a href="/">Volver al chat</a>
        </div>
    </body>
    </html>
    """

@app.route("/pago_cancelado")
def pago_cancelado():
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Pago Cancelado</title>
        <style>
            body { font-family: Arial; text-align: center; padding: 50px; background: #ffe6f0; }
            .error { background: white; padding: 40px; border-radius: 15px; max-width: 500px; margin: 0 auto; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
            .error h1 { color: #dc3545; }
            a { display: inline-block; margin-top: 20px; padding: 12px 24px; background: #d63384; color: white; text-decoration: none; border-radius: 8px; }
            a:hover { background: #a32461; }
        </style>
    </head>
    <body>
        <div class="error">
            <h1>❌ Pago Cancelado</h1>
            <p>Has cancelado el proceso de suscripción.</p>
            <a href="/">Volver al chat</a>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
