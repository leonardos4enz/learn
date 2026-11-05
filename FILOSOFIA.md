# Filosofía de Mi Tutor

> **La regla que no se rompe:** todo lo que hace Mi Tutor tiene un *cómo* y un *porqué*, y el porqué
> sale de estudios reales sobre cómo aprende la gente. Si una función nueva no tiene respaldo, se
> marca como **hipótesis** y se mide; no se presenta como hecho.

Leo construyó esta app porque los cursos en video le aburrían y no se le quedaban. La meta no es
"terminar el curso" sino **entender y recordar**. Este documento es la esencia de la app: léelo
antes de cambiar el método, la interfaz o las skills (`tutor`, `ingestar`).

## 1. Las técnicas de estudio (qué hacemos y por qué)

| Qué hace la app | Técnica | Evidencia |
|---|---|---|
| Cada sesión abre con 3 preguntas **de memoria**; hojas y tarjetas piden recordar sin ver | **Práctica de recuerdo** (*retrieval / practice testing*) | Dunlosky et al. (2013): una de solo **dos** técnicas de "alta utilidad" entre diez. |
| Tarjetas diarias (FSRS), hojas al día siguiente, preguntas de hace 1, 3 y 7+ sesiones | **Repaso espaciado** (*distributed practice*) | Dunlosky et al. (2013), la otra de alta utilidad; Cepeda et al. (2006), revisión de 317 experimentos. FSRS es el algoritmo actual de Anki. |
| **No** se releen apuntes, ni se subraya, ni se resume como método principal | Técnicas de baja utilidad | Dunlosky et al. (2013): releer, subrayar y resumir salieron de baja utilidad. |
| El tutor **no da la respuesta de entrada**; Leo predice, diseña, revisa y rompe | IA con *guardrails* | Bastani et al. (PNAS 2025): con un chatbot sin reglas, los alumnos practicaron mejor pero sacaron **17% menos** en el examen sin IA; con un tutor que no daba respuestas, el daño casi desapareció. |
| Sesiones guiadas con preguntas en los momentos clave | Tutoría con diseño pedagógico | Kestin et al. (Harvard, *Sci. Reports* 2025): un tutor de IA bien diseñado superó a una clase de aprendizaje activo (sin medición a largo plazo). |
| En un tema **nuevo**, primero explicación y ejemplo resuelto; después predecir | *Worked examples* / *expertise reversal* | Kirschner, Sweller y Clark (2006): la instrucción con poca guía rinde menos en novatos; con más dominio, conviene dar menos ayuda. |
| **Lecciones** (vista Lecciones): cada misión tiene su lección guardada, en este orden fijo: el problema → explicación con un ejemplo resuelto y su código completo → 2–4 pasos *predice* → resumen | *Worked examples* + práctica de recuerdo + segmentación | Kirschner, Sweller y Clark (2006) para el orden; Dunlosky et al. (2013) para predecir al final; Mayer (segmentación, d ≈ 0.7) para un concepto por paso. |
| En los pasos *predice* de una lección hay que **escribir** la respuesta antes de verla, y después decir si acertó | Generación / práctica de recuerdo | Dunlosky et al. (2013). Guardar la predicción y el "¿acertaste?" deja que el tutor empiece la sesión por lo que falló. La autoevaluación de Leo es **hipótesis**: puede sobrestimarse; el examen sin IA es la medida real. |
| Al terminar una lección, sus tarjetas entran solas al mazo FSRS | Repaso espaciado | Cepeda et al. (2006). |
| **Leer no es saber**: al terminar, la lección queda *leída*; solo el **tutor** la marca *verificada* (o *repasar*) cuando Leo contesta sin ayuda en la sesión. El score cuenta solo las verificadas | Evaluación externa, sin ayuda | Dunlosky y Rawson (2012): juzgamos mal lo que sabemos justo después de estudiarlo, y esa sobreconfianza hace que se estudie menos de lo necesario. Bastani et al. (2025): medir sin ayuda. |
| Cada pregunta *predice* se contesta con lo que hay en pantalla: el código va en la pregunta, o un botón abre el del ejemplo | Recuerdo, no adivinanza | Predecir sirve si el error muestra un malentendido; sin el código, el error solo muestra que faltaba información. Vino de Leo (registrado en Mejoras). |
| La lección **no se relee** como forma de estudiar: después de leerla una vez, se practica en la sesión y se repasa con tarjetas y hojas | Releer es de baja utilidad | Dunlosky et al. (2013). |
| La sesión con el tutor empieza **desde la lección**: si ya la leyó, el tutor no la repite y empieza por sus predicciones falladas | *Expertise reversal* | Kalyuga (2007): la guía que ayuda al novato estorba cuando ya se sabe; repetir la explicación completa gastaría la sesión. |
| Las lecciones se generan del material del curso con la skill `ingestar`: primero el temario, que Leo aprueba; el código se corre antes de publicarlo | Calidad del ejemplo resuelto | Un ejemplo resuelto con errores enseña el error. Verificar el código es la condición para que el ejemplo valga. |
| Predecir antes de correr el código o ver la respuesta | Generación + práctica de recuerdo | Los errores de predicción muestran el malentendido exacto; se combinan con explicación inmediata. |
| Proyecto propio y aprender "cuando se necesita"; compararse con uno mismo | Aprendizaje por proyecto | Consejo de Andrej Karpathy (opinión de experto, no estudio controlado). |
| Ver una versión mini por dentro (nanograph) | Abrir la caja negra | Estilo de enseñanza de Karpathy (micrograd, nanoGPT); opinión de experto. |
| Exámenes de módulo **sin IA** y con umbral de 70% | Medir aprendizaje real | Bastani et al. (2025): practicar con IA puede verse bien sin dejar aprendizaje; hay que medir sin ayuda. |

## 2. Cómo se presenta la información (diseño de la interfaz)

| Decisión | Principio | Evidencia |
|---|---|---|
| La explicación va **al lado** del diagrama o código | Contigüidad espacial | Mayer: el principio con mayor efecto (mediana d ≈ 1.1 en su resumen de 2014). |
| Nada decorativo: sin emojis, chistes ni datos curiosos en el contenido; animaciones mínimas | Coherencia / *seductive details* | Mayer (coherencia, d ≈ 0.86); Sundararajan y Adesope (2020): los detalles atractivos pero irrelevantes empeoran el aprendizaje (g ≈ −0.33). |
| Resaltar solo lo clave (1 nodo, 1–3 líneas) | Señalización | Mayer (d ≈ 0.4). |
| Un concepto por paso, avanzar a tu ritmo (← →) | Segmentación | Mayer (d ≈ 0.7); el daño de los *seductive details* es mayor sin control del ritmo. |
| Barra de progreso por segmentos en las lecciones (cuántos pasos faltan; los *predice* marcados) | Segmentación + saber cuánto falta | Mayer (segmentación). Que la barra motive es **hipótesis** (estilo Duolingo, sin estudio controlado aquí). |
| Camino de lecciones por módulo, con el grokpet junto a la que toca | Gusto de Leo; menos decisiones | **Hipótesis**: estilo Duolingo. Mostrar "la que toca" reduce el costo de decidir por dónde seguir; no hay estudio que lo respalde para este caso. |
| Código siempre **completo**; las líneas largas bajan en vez de esconderse | Coherencia: nada que reconstruir | Viene de la primera sesión: Leo se confundía con código recortado (registrado en Mejoras). |
| Imágenes solo si enseñan algo; los grafos van en diagrama, no en captura | Coherencia | Mayer (coherencia); Sundararajan y Adesope (2020). |
| La **pantalla en vivo es solo para ver**: no tiene campos de texto; Leo contesta en el chat y en *Predice* revela la respuesta después de decirla | Práctica de recuerdo sin duplicar trabajo | Dunlosky et al. (2013). La app no le pasa al tutor lo que se escribe en la pantalla, así que escribir ahí era trabajo perdido y Leo terminaba contestando dos veces. |
| **Recorrido**: un grafo paso a paso, con el node activo iluminado y el state de ese momento al lado; Leo avanza con ← → | Animación de un proceso + segmentación + señalización | Höffler y Leutner (2007), meta-análisis: las animaciones superan a las imágenes quietas sobre todo en conocimiento de procedimientos (d ≈ 0.4). Mayer y Chandler (2001): que el alumno controle el ritmo de los pasos ayuda. |
| **Estado**: antes / update / después, con las keys que cambiaron resaltadas | Señalización | Mayer (señalización, d ≈ 0.4): marca justo lo que hizo el reducer. |
| **Comparar**: dos versiones de código lado a lado con las líneas distintas marcadas | Comparación de casos + contigüidad | Alfieri, Nokes-Malach y Schunn (2013), meta-análisis: aprender comparando casos rinde más que verlos por separado (d ≈ 0.5). Mayer (contigüidad). |
| Diagramas con **nodes que se tocan** para ver su explicación al lado | Contigüidad + control del alumno | Mayer (contigüidad). Que tocar ayude más que leer todas las notas es **hipótesis**. |
| **Plan de hoy** en Hoy: pasos concretos y en orden (tarjetas → lección → sesión → hoja), con check al cumplirlos | Intenciones de implementación | Gollwitzer y Sheeran (2006), meta-análisis: decidir de antemano qué hacer y cuándo aumenta mucho que se haga (d ≈ 0.65). El orden sigue lo de arriba: recordar primero, ejemplo resuelto antes de practicar, papel al final. |
| **Racha** (días seguidos con tarjetas, una lección o una sesión), fuego animado y celebración la primera vez del día | Hábito diario | **Hipótesis** (estilo Duolingo): que motive no está probado aquí. Lally et al. (2010): un día que se salta no rompe la formación del hábito, por eso el texto nunca regaña. Silverman y Barasch (2023): perder una racha baja el compromiso, así que si se rompe se dice sin drama y basta un repaso para empezar otra. La celebración sale **después** de terminar algo, nunca a mitad de una lección. |
| **Score** por módulo, curso y rama en Mis estudios: promedio de misiones hechas, lecciones leídas, tarjetas dominadas (≥21 días) y examen del módulo | Medir lo que importa, de forma transparente | Cómo se combinan las partes es **decisión nuestra**, no un estudio; por eso cada módulo muestra sus partes. Incluye tarjetas dominadas y examen para que el número mida si **recuerdas**, no solo si avanzaste (Cepeda et al. 2006; Bastani et al. 2025). Las ramas promedian sus cursos y los no empezados cuentan 0. |
| Camino de lecciones **ondulado**, con botones "3D" y burbuja "Empezar" sobre la que toca | Gusto de Leo; ver dónde vas | **Hipótesis** (estilo Duolingo). Dibujo y animaciones propios: no se usa arte de Duolingo. |
| Tarjetas que **giran** al voltearse y salen al calificarse (< 250 ms) | Señalar el cambio de estado | **Hipótesis**/gusto. Cortas para no distraer y apagadas con "reducir movimiento". |
| **Sonidos** sintetizados (acierto, error, voltear, lección terminada, racha), con botón para apagarlos | Retroalimentación inmediata | **Hipótesis**. La retroalimentación inmediata ayuda (Hattie y Timperley 2007), pero el sonido solo dice "bien/mal", no enseña; por eso nunca suena sobre el contenido y se puede apagar. |
| Texto de los botones de color con contraste completo (también la tecla "espacio") | Legibilidad | WCAG 1.4.3: contraste mínimo 4.5:1. En modo oscuro el botón usa texto oscuro porque el verde es claro. |
| Modo claro por defecto (texto oscuro sobre fondo claro) | Polaridad positiva | Piepenbrock et al. (2013, 2014). |
| Texto de 16–17 px, interlineado 1.6, líneas de ~70 caracteres | Legibilidad | Dyson (2004): preferencia por 45–72 caracteres; WCAG 1.4.8 (máx. 80). Convención, evidencia limitada. |
| Fuente Nunito (redondeada, estilo Duolingo) | Gusto de Leo | No hay ganador claro entre fuentes legibles (Nielsen; estudios mixtos). Fuentes "difíciles" como Sans Forgetica **no** ayudan (Taylor et al. 2020). |
| Botón «?» en cada vista con su razón de ser | Transparencia del método | Para que el porqué nunca se pierda. |

## 3. Papel e impresión

- Las hojas se resuelven **en papel, al día siguiente, sin computadora**: junta recuerdo y espaciado.
- Leer textos técnicos en papel se comprende un poco mejor que en pantalla (meta-análisis de Delgado et al. 2018, efecto ≈ 0.21).
- **Mito que no repetimos:** "escribir a mano memoriza mejor". El estudio famoso (Mueller y
  Oppenheimer 2014) no se sostuvo en las réplicas (Morehead, Dunlosky y Rawson 2019). El papel ayuda
  porque no hay dónde buscar la respuesta, no por magia.
- Las respuestas **no se imprimen**: se revisan en la app.

## 4. Mitos y cosas que no hacemos

- Releer o ver el video otra vez como forma de estudiar.
- Fuentes "difíciles" para memorizar.
- Prometer que una herramienta "garantiza" aprender: lo que se puede asegurar es que cada parte usa
  técnicas con evidencia, y los exámenes sin IA muestran si funciona.
- Repasar "varias veces al día": el repaso espaciado se mide en **días**; basta una sesión diaria.

## 5. Cómo cambiar la app sin perder esto

1. Toda función nueva dice **qué técnica aplica y con qué evidencia**, o se marca como hipótesis.
2. Su botón «?» (o su texto de ayuda) explica el porqué en lenguaje simple.
3. Las mejoras y errores que detecten Leo o el tutor se registran en la vista **Mejoras** (tabla
   `mejoras`, herramienta MCP `registrar_mejora`) con quién lo reportó, el curso y su estado
   (nueva / aceptada / hecha / descartada). El tutor registra lo que notó al cerrar cada sesión y
   revisa las abiertas al empezar. Se revisan antes de cambiar el método; una mejora que contradiga
   este documento se discute primero.
4. Si un estudio nuevo contradice algo de aquí, se actualiza este documento primero y después el código.

## Fuentes

- Dunlosky, Rawson, Marsh, Nathan y Willingham (2013). *Improving Students' Learning With Effective Learning Techniques*. Psychological Science in the Public Interest.
- Cepeda, Pashler, Vul, Wixted y Rohrer (2006). *Distributed practice in verbal recall tasks*. Psychological Bulletin 132(3).
- Bastani et al. (2025). *Generative AI without guardrails can harm learning*. PNAS 122.
- Kestin et al. (2025). *AI tutoring outperforms in-class active learning*. Scientific Reports 15, 17458.
- Kirschner, Sweller y Clark (2006). *Why minimal guidance during instruction does not work*. Educational Psychologist.
- Dunlosky y Rawson (2012). *Overconfidence produces underachievement: Inaccurate self evaluations undermine students' learning and retention*. Learning and Instruction 22(4).
- Gollwitzer y Sheeran (2006). *Implementation Intentions and Goal Achievement: A Meta-analysis of Effects and Processes*. Advances in Experimental Social Psychology 38.
- Lally, van Jaarsveld, Potts y Wardle (2010). *How are habits formed: Modelling habit formation in the real world*. European Journal of Social Psychology 40(6).
- Silverman y Barasch (2023). *On or Off Track: How (Broken) Streaks Affect Consumer Decisions*. Journal of Consumer Research 49(6).
- Hattie y Timperley (2007). *The Power of Feedback*. Review of Educational Research 77(1).
- Höffler y Leutner (2007). *Instructional animation versus static pictures: A meta-analysis*. Learning and Instruction 17(6).
- Mayer y Chandler (2001). *When learning is just a click away: Does simple user interaction foster deeper understanding of multimedia messages?* Journal of Educational Psychology 93(2).
- Alfieri, Nokes-Malach y Schunn (2013). *Learning Through Case Comparisons: A Meta-Analytic Review*. Educational Psychologist 48(2).
- Kalyuga (2007). *Expertise Reversal Effect and Its Implications for Learner-Tailored Instruction*. Educational Psychology Review 19.
- Mayer, *Multimedia Learning* (principios de contigüidad, coherencia, señalización y segmentación).
- Sundararajan y Adesope (2020). *Keep it Coherent: A Meta-Analysis of the Seductive Details Effect*. Educational Psychology Review 32.
- Piepenbrock, Mayr, Mund y Buchner (2013). *Positive display polarity is advantageous for both younger and older adults*. Ergonomics 56(7).
- Delgado, Vargas, Ackerman y Salmerón (2018). *Don't throw away your printed books*. Educational Research Review 25.
- Morehead, Dunlosky y Rawson (2019). *How Much Mightier Is the Pen than the Keyboard for Note-Taking?* Educational Psychology Review 31.
- Taylor, Sanson, Burnell, Wade y Garry (2020). *Disfluent difficulties are not desirable difficulties: the (lack of) effect of Sans Forgetica on memory*. Memory 28(7).
- Dyson (2004). *How physical text layout affects reading from screen*. Behaviour & Information Technology.
