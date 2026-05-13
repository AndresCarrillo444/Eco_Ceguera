# 🦇 Eco-Ceguera

Un juego de sigilo, estrategia y supervivencia basado puramente en la **ecolocalización**. Tu pantalla está sumida en la oscuridad total; tu única forma de ver el laberinto, esquivar enemigos y encontrar la salida es utilizando pulsos de sonar. Pero ten mucho cuidado: **los enemigos también pueden escuchar tu sonar y tus pasos**.

## 🌟 Características Principales

* **Mecánica Única de Sonar:** Navega a ciegas emitiendo pulsos direccionales o de 360°. El sonido rebota en paredes y revela elementos, pero alerta a los monstruos.
* **Múltiples Enemigos:** Desde monstruos básicos que reaccionan al ruido, hasta murciélagos con su propio sonar, *Stalkers* que cazan en silencio, y *Mímicos* que se disfrazan de la salida.
* **Entornos Interactivos:** Charcos ruidosos, vidrios rotos que delatan tu posición, zonas de viento que bloquean el sonido, y paredes de espejo que duplican tus pulsos.
* **Campaña de 9 Niveles:** Desafiantes laberintos generados proceduralmente que introducen nuevas mecánicas, incluyendo "Apagón" y "Cuenta Regresiva".
* **Editor de Niveles Integrado:** Diseña, juega y guarda tus propios laberintos personalizados.
* **Modo Cooperativo Local:** Juega acompañado de un segundo jugador en el mismo teclado para distraer enemigos y completar los niveles en equipo.
* **Leaderboards (Local y Global):** Compite por el mejor tiempo del mundo gracias a la integración con Firebase Realtime Database.
* **Audio Procedural:** Generación de efectos de sonido en tiempo real utilizando ondas matemáticas con `numpy`.

---

## 🛠️ Requisitos

Para poder correr el juego de forma óptima, necesitas:
* Python 3.8 o superior.
* `pygame` (Manejo de gráficos, bucle de juego, eventos y ventana).
* `numpy` (Síntesis procedural de sonidos y acústica rápida).

## 🚀 Instalación y Uso

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/AndresCarrillo444/eco-ceguera.git
   cd eco-ceguera
   ```

2. **Instalar dependencias:**
   ```bash
   pip install pygame numpy
   ```

3. **Ejecutar el juego:**
   ```bash
   python eco-ceguera.py
   ```

---

## 🎮 Controles

### Jugador 1
* **WASD:** Moverse (genera ruido al correr).
* **Shift Izquierdo:** Modo Sigilo (movimiento lento, silencia tus pisadas).
* **Clic Izquierdo:** Pulso Sonar 360° (revela un área circular grande, alerta enemigos lejanos).
* **F:** Sonar Direccional (emite un cono concentrado hacia el mouse, útil para no hacer tanto eco).
* **Q + Clic:** Lanzar piedra (genera una distracción ruidosa en el lugar de impacto).
* **Clic Derecho:** Señuelo Sónico (deja un emisor falso que atrapa la atención de los monstruos).
* **E:** Absorción de Sonido (habilidad que silencia temporalmente tu ruido y micro-pulsos durante 3 segundos).
* **C (En partida):** Activar / Desactivar la aparición del Jugador 2 (Cooperativo).
* **R:** Reiniciar el nivel rápidamente.
* **ESC:** Menú de pausa o volver atrás.

### Jugador 2 (Co-op Local)
* **Flechas Direccionales:** Moverse.
* **Shift Derecho (RShift):** Modo Sigilo.

---

## 🧠 Enemigos y Peligros
* **Rastreador (Rojo):** Enemigo básico. Persigue el origen de cualquier ruido fuerte (correr, lanzar piedras, clics de sonar).
* **Murciélago (Carmín):** Emite su propio sonar constantemente; si su onda te toca, te detectará.
* **Pesado (Naranja):** Monstruo lento pero letal. Escucha tus pulsos y pasos desde distancias enormes.
* **Sombra Silenciosa:** Te caza rápidamente si abusas del sonar. Es casi imperceptible en la oscuridad.
* **El Mímico:** Un monstruo que copia el color y la forma cuadrada de la salida dorada. Acércate con precaución para verificar que es la puerta real.

---

## 🗺️ Editor de Niveles
Accede al editor desde el menú principal para dibujar tus propios laberintos personalizados:
- Usa la **rueda del ratón** o las teclas numéricas **(1-8)** para cambiar el bloque a pintar (Muro, Pasillo, Salida, Trampas, Enemigos, etc.).
- Haz **clic izquierdo** para pintar el bloque seleccionado sobre el mapa.
- Usa el botón de **Guardar** en la parte inferior para nombrar tu nivel. Aparecerá en tu pestaña de "Mis Niveles" listo para jugar.

---

## 🌐 Configurar Leaderboard Global (Opcional)
El juego incluye integración para registrar los puntajes a nivel mundial. Si clonas el proyecto y deseas utilizar tu propia base de datos:
1. Crea un proyecto gratuito en [Firebase](https://firebase.google.com/).
2. Accede a **Realtime Database** y crea una base de datos eligiendo *Start in test mode*.
3. Copia la URL que se te asigna (por ejemplo: `https://mi-proyecto-default-rtdb.firebaseio.com/`).
4. Abre el archivo `eco_online_lb.py` e inserta tu link en la variable `FIREBASE_URL = "..."`.

---

## 👨‍💻 Créditos
- **Diseño, Arte y Código:** Andrés Carrillo ([@AndresCarrillo444](https://github.com/AndresCarrillo444))
- **Tecnología:** Escrito enteramente en Python usando la librería Pygame.
