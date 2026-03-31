# 🐍 Visual Python IDE — Low-Code App Builder

Visual Python es un entorno de desarrollo integrado (IDE) diseñado para crear aplicaciones de escritorio modernas con `customtkinter` de forma visual y rápida, eliminando la necesidad de escribir código repetitivo.

---

## 🎨 Diseño Visual (Visual Canvas)
- **Editor WYSIWYG:** Arrastra y suelta componentes directamente en el lienzo.
- **Sistema de Grilla (Grid 12x12):** Alineación perfecta y simétrica de widgets mediante "snapping" automático.
- **Vistas Múltiples:** Crea aplicaciones con varias ventanas/pantallas y gestiona su navegación de forma visual.
- **Colores y Estilos:** Personaliza colores de fondo, texto, bordes y radios de esquina en tiempo real.

## 🔗 Lógica por Nodos (No-Code Engine)
- **Programación Visual Estructurada:** Conecta eventos (clics, pulsaciones) con Nodos de Acción y Decisión.
- **Decision Nodes (Rombo):** Crea bifurcaciones lógicas (`True/False`) fácilmente comparando valores exactos, widgets o múltiples variables (`==`, `<`, `>`).
- **Sistema Local y Global de Variables:** 
    - Guarda información ingresada (`save_variable`).
    - Define variables globales persistentes con tipos explícitos (`Texto`, `Número`, `Bool`) a través del panel `🔧 Manage Variables`.
- **Interpretador Universal:** 
    - Imprime y concatena datos dinámicos en tiempo real evaluando el formato abstracto `{nombre_variable}`.
    - Las llaves reaccionan inteligente y automáticamente buscando primero un Entry de la UI, luego variables globales, o dejando strings por defecto. Soporte nativo y transversal al iniciar la app.
- **Navegación:** Cambia de vista (`change_view`) visualmente uniendo nodos.

## 🛠️ Widgets Disponibles
- **Labels:** Muestra textos estáticos o variables en crudo al arrancar.
- **Buttons:** Lanzadores de eventos modulares.
- **Text Entry (🔤):** Cajas para strings clásicas (`CTkEntry`).
- **Number Entry (🔢):** Cajas preparadas paramétricamente para lógicas matemáticas (`CTkEntryNum`).

## ⚙️ Características Core
- **Generación de Código Limpio:** Produce código Python profesional basado en clases, listo para ser ejecutado o modificado.
- **Historial Seguro (Undo/Redo):** Retrocede o avanza tus acciones (hasta 5 pasos) para experimentar sin miedo.
- **Previsualización en Vivo:** Prueba tu aplicación al instante en un subproceso real antes de exportarla.
- **Nombramiento Global Unico:** Gestión automática de nombres de variables para evitar colisiones en proyectos grandes.
- **Exportación:** Exporta tu proyecto como un archivo `.py` independiente o compílalo.

---

## 🚀 Cómo empezar
Para iniciar el IDE, asegúrate de tener instalado `customtkinter` y ejecuta:

```bash
python main.py
```

*Desarrollado para potenciar la creación de interfaces Python de forma rápida y profesional.*
