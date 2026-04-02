# 🐍 Visual Python IDE v1.12 — "Object-Variable Binding"

Visual Python es un entorno de desarrollo integrado (IDE) low-code diseñado para crear aplicaciones profesionales con `customtkinter` de forma visual. La versión 1.12 introduce una arquitectura orientada a datos y lógica multi-hilo escalable.

---

## 🎨 Diseño Visual (Visual Canvas)
- **Editor WYSIWYG:** Arrastra y suelta componentes directly en el lienzo.
- **Sistema de Grilla (Grid 12x12):** Alineación perfecta y simétrica mediante "snapping".
- **Vistas Múltiples:** Crea aplicaciones complejas con navegación fluida entre pantallas.
- **Data Binding (v1.12):** Vincula Widgets de entrada (Entries) directamente a variables globales usando **Var Key**. Tus variables se sincronizan automáticamente mientras el usuario escribe.

## 🔗 Lógica por Nodos (Pro Engine)
- **Multi-Task Actions:** Los nodos de acción ahora son **secuenciadores**. Un solo nodo puede ejecutar múltiples tareas en orden (cambiar textos, guardar variables, navegar) ahorrando espacio en el canvas.
- **Pro Decision Nodes (ELIF Branching):** Evolución del rombo clásico. Ahora soporta múltiples condiciones (`IF`, `ELIF`, `ELSE`) en un solo nodo.
    - **Puertos Intuitivos:** Visualiza ramas con etiquetas claras: `S` (Sí/Verdadero), `N` (No/Falso) o `C0`, `C1`... para lógicas complejas.
- **Smart Logic Comparison:** Motor de comparación inteligente que detecta tipos de datos. Compara `5` y `5.0` de forma numérica automáticamente, evitando errores de tipo comunes en Python.
- **Variables Globales Dinámicas:** 
    - Usa `{mi_variable}` en cualquier campo de texto. El motor buscará primero en los widgets activos, luego en el diccionario global `self._vars` y finalmente en literales.
- **Navegación Avanzada:** Gestión visual de flujos de usuario mediante conexiones lógicas.

## 🛠️ Widgets Disponibles
- **Labels:** Etiquetas dinámicas con soporte para plantillas `{var}`.
- **Buttons:** Gatillos de eventos modulares y estilizados.
- **Text Entry (🔤):** Cajas de texto con auto-sincronización de datos.
- **Number Entry (🔢):** Entradas numéricas con validación paramétrica.

## ⚙️ Características Core
- **Generación de Código Robusta:** Produce archivos Python limpios y legibles basados en clases POO.
- **Previsualización en Vivo (F5):** Ejecuta un subproceso real para testear tu app al instante.
- **Snap-to-Grid:** Mantén tus diseños limpios y alineados sin esfuerzo.
- **Undo/Redo:** Historial de acciones para experimentar sin riesgos.
- **Exportación Total:** Genera archivos `.py` o compila ejecutables `.exe` directamente.

---

## 🚀 Cómo empezar
Para iniciar el IDE, asegúrate de tener instalado `customtkinter` y `Pillow`:

```bash
pip install customtkinter pillow
python main.py
```

*Visual Python v1.12: Potenciando la creación de interfaces Python de forma rápida, profesional e intuitiva.*

