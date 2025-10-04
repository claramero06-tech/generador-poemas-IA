// ========================================
// SISTEMA DE PRUEBA GRATUITA Y SUSCRIPCIÓN
// ========================================

let tiempoRestante = 3600; // 1 hora en segundos
let tiempoInicio;
let intervalo;
let pruebaExpirada = false;

// Verificar si ya usó la prueba gratuita
function inicializarPrueba() {
  const suscripcionActiva = localStorage.getItem('suscripcionActiva');
  
  if (suscripcionActiva === 'true') {
    // Usuario ya pagó
    document.getElementById('tiempoRestante').style.display = 'none';
    return;
  }

  const tiempoGuardado = localStorage.getItem('tiempoInicioPrueba');
  
  if (tiempoGuardado) {
    // Ya había iniciado la prueba antes
    tiempoInicio = parseInt(tiempoGuardado);
    const tiempoTranscurrido = Math.floor((Date.now() - tiempoInicio) / 1000);
    tiempoRestante = 3600 - tiempoTranscurrido;
    
    if (tiempoRestante <= 0) {
      mostrarModalExpirado();
      return;
    }
  } else {
    // Primera vez que entra
    tiempoInicio = Date.now();
    localStorage.setItem('tiempoInicioPrueba', tiempoInicio);
  }
  
  iniciarContador();
}

// Contador regresivo
function iniciarContador() {
  actualizarContador();
  
  intervalo = setInterval(() => {
    tiempoRestante--;
    
    if (tiempoRestante <= 0) {
      clearInterval(intervalo);
      mostrarModalExpirado();
    } else {
      actualizarContador();
    }
  }, 1000);
}

// Actualizar display del contador
function actualizarContador() {
  const minutos = Math.floor(tiempoRestante / 60);
  const segundos = tiempoRestante % 60;
  const display = `${minutos}:${segundos.toString().padStart(2, '0')}`;
  document.getElementById('contador').textContent = display;
  
  // Cambiar color cuando quedan menos de 5 minutos
  if (tiempoRestante < 300) {
    document.getElementById('tiempoRestante').style.background = '#ffcccc';
    document.getElementById('tiempoRestante').style.color = '#cc0000';
  }
}

// Mostrar modal cuando expira el tiempo
function mostrarModalExpirado() {
  pruebaExpirada = true;
  document.getElementById('modalTiempoExpirado').style.display = 'block';
  document.getElementById('tiempoRestante').innerHTML = '❌ Prueba gratuita finalizada';
  document.getElementById('tiempoRestante').style.background = '#ffcccc';
  document.getElementById('tiempoRestante').style.color = '#cc0000';
  
  // Bloquear inputs
  document.getElementById('mensaje').disabled = true;
  document.getElementById('enviarBtn').disabled = true;
}

// Verificar si tiene acceso
function verificarAcceso() {
  // Verificar si tiene suscripción activa
  const suscripcionActiva = localStorage.getItem('suscripcionActiva');
  if (suscripcionActiva === 'true') {
    return true;
  }

  // Verificar si expiró la prueba
  const tiempoInicio = localStorage.getItem('tiempoInicioPrueba');
  if (!tiempoInicio) {
    return true; // Primera vez
  }

  const tiempoTranscurrido = Math.floor((Date.now() - parseInt(tiempoInicio)) / 1000);
  if (tiempoTranscurrido >= 3600) {
    return false; // Expiró
  }

  return true;
}

// ========================================
// FUNCIONALIDAD DEL CHAT
// ========================================

// Muestra "Escribiendo..."
function mostrarPensando(chatBox) {
  const pensando = document.createElement("div");
  pensando.classList.add("mensaje", "ia", "pensando");
  pensando.innerHTML = "Escribiendo<span class='dot'>.</span><span class='dot'>.</span><span class='dot'>.</span>";
  pensando.id = "mensaje-pensando";
  chatBox.appendChild(pensando);
  chatBox.scrollTop = chatBox.scrollHeight;
  return pensando;
}

// Escritura tipo máquina
function escribirPocoAPoco(elemento, texto, velocidad = 30) {
  elemento.textContent = "";
  let i = 0;
  const intervalo = setInterval(() => {
    elemento.textContent += texto.charAt(i);
    i++;
    if (i >= texto.length) clearInterval(intervalo);

    const chatBox = document.getElementById("chat-box");
    chatBox.scrollTop = chatBox.scrollHeight;
  }, velocidad);
}

// === Guardar historial en localStorage ===
function guardarHistorial() {
  const chatBox = document.getElementById("chat-box");
  localStorage.setItem("chatHistorial", chatBox.innerHTML);
}

// === Cargar historial desde localStorage ===
function cargarHistorial() {
  const chatBox = document.getElementById("chat-box");
  const historial = localStorage.getItem("chatHistorial");
  if (historial) chatBox.innerHTML = historial;
}

// Función principal para enviar mensaje
async function enviarMensaje() {
  // ⚠️ VERIFICAR ACCESO ANTES DE ENVIAR
  if (!verificarAcceso()) {
    alert("⏰ Tu prueba gratuita ha terminado. Por favor, suscríbete para continuar.");
    mostrarModalExpirado();
    return;
  }

  const input = document.getElementById("mensaje");
  const chatBox = document.getElementById("chat-box");
  const btn = document.getElementById("enviarBtn");

  let texto = input.value.replace(/\r\n/g, '\n');
  if (texto.trim().length === 0) return;

  // Mensaje del usuario
  const userMsg = document.createElement("div");
  userMsg.classList.add("mensaje", "usuario");
  userMsg.textContent = texto;
  chatBox.appendChild(userMsg);

  input.value = "";
  input.style.height = "";
  
  // Deshabilitar botón mientras procesa
  btn.disabled = true;

  // Mostrar "pensando..."
  const pensando = mostrarPensando(chatBox);

  try {
    const response = await fetch("/generar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mensaje: texto })
    });

    const data = await response.json();

    pensando.remove();

    // Mensaje de la IA
    const iaMsg = document.createElement("div");
    iaMsg.classList.add("mensaje", "ia");
    chatBox.appendChild(iaMsg);

    escribirPocoAPoco(iaMsg, data.respuesta, 25);

  } catch (error) {
    pensando.remove();
    const errorMsg = document.createElement("div");
    errorMsg.classList.add("mensaje", "ia");
    errorMsg.textContent = "❌ Error al generar respuesta.";
    chatBox.appendChild(errorMsg);
    console.error(error);
  } finally {
    btn.disabled = false;
  }

  chatBox.scrollTop = chatBox.scrollHeight;

  // Guardar en historial
  guardarHistorial();
}

// ========================================
// INICIALIZACIÓN
// ========================================

document.addEventListener("DOMContentLoaded", () => {
  // Cargar historial previo
  cargarHistorial();

  // Inicializar sistema de prueba gratuita
  inicializarPrueba();

  // Configurar eventos del chat
  const input = document.getElementById("mensaje");
  const btn = document.getElementById("enviarBtn");

  btn.addEventListener("click", enviarMensaje);

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      enviarMensaje();
    }
  });

  // Auto-resize del textarea
  input.addEventListener("input", function() {
    this.style.height = "auto";
    this.style.height = (this.scrollHeight) + "px";
  });
});