"""Diálogos redactados para una carga de actividad con anotaciones verificables.

API pública: ``construir_dialogo(indice, perfil, rng)``. ``perfil`` necesita
``nombre``, ``dificultades`` y ``recursos`` (listas de los códigos del sistema).
``voz`` y ``contexto_idx`` son opcionales. La salida contiene pares de mensajes,
sus citas literales y un ``bloque`` de 0 a 4 para colocar pausas en el calendario.

Este módulo no invoca un modelo ni afirma haberlo hecho: las evidencias son
anotaciones estructuradas de estos textos. La importación y el resumen utilizan
las reglas y los agregadores del proyecto. No produce diagnósticos ni puntajes.
"""

from collections import Counter
from fractions import Fraction
import re

try:
    from .contextos_extra import CONTEXTOS_EXTRA
except ImportError:
    CONTEXTOS_EXTRA = ()


DIFICULTADES = (
    'sobrecarga_academica', 'presion_tiempo',
    'sintomas_fisicos', 'sintomas_psicologicos',
)
RECURSOS = ('planificacion', 'automotivacion', 'busqueda_soporte')
VOCES = ('breve', 'coloquial', 'detallista', 'serena')


# Cada contexto tiene preguntas y respuestas que se retoman en orden. No son
# frases intercambiadas al azar entre asignaturas ni citas de supuestos alumnos.
CONTEXTOS = (
    {
        'area': 'Comunicación', 'tarea': 'una exposición sobre publicidad',
        'detalle': 'Elegí un anuncio de zapatillas. Lo raro es que casi no dice nada del producto, todo es gente pasándola bien.',
        'detalle_bot': 'Ese contraste te sirve: puedes diferenciar lo que informa del producto y la emoción que intenta asociarle.',
        'pregunta': 'Entonces, ¿una imagen también puede ser un argumento? Yo pensaba que argumento era solo lo escrito.',
        'respuesta': 'Puede apoyar la persuasión, aunque no siempre demuestra una afirmación. En tu anuncio, la imagen sugiere una vida deseable; eso es distinto de probar la calidad de las zapatillas.',
        'segunda': 'Ya, sería como que te venden la sensación de pertenecer a ese grupo. ¿Eso puedo ponerlo como idea central?',
        'respuesta_segunda': 'Sí, si explicas qué detalle de la imagen te lleva a esa lectura. Puedes presentarlo como tu interpretación y distinguirlo de los datos que el anuncio sí ofrece.',
        'practica': 'Escribí esto: “El anuncio asocia las zapatillas con pertenecer a un grupo, aunque no explica sus materiales”.',
        'practica_bot': 'La comparación se entiende y se apoya en algo observable. Si añades un detalle de la escena, tu explicación quedará más concreta.',
        'avance': 'Al final escogí la escena donde todos usan el mismo modelo. Ya tengo el ejemplo para explicar mi idea.',
        'avance_bot': 'Ese detalle conecta bien con tu idea sobre pertenencia. Puedes usarlo para que quien te escuche siga tu razonamiento.',
        'curiosidad': 'Ahora veo anuncios por todos lados y me fijo en cosas que antes ni miraba jaja.',
        'curiosidad_bot': 'Pasa cuando encuentras una forma nueva de mirar algo cotidiano. Hasta una publicidad del paradero puede darte otro ejemplo.',
    },
    {
        'area': 'Matemática', 'tarea': 'unos ejercicios de probabilidad',
        'detalle': 'En uno hay bolitas de colores en una bolsa. Son cuatro rojas y seis azules; te piden sacar dos sin devolver la primera.',
        'detalle_bot': 'La parte clave es que la primera extracción cambia cuántas bolitas quedan para la segunda.',
        'pregunta': 'Para que las dos sean rojas, ¿sería cuatro décimos por cuatro décimos?',
        'respuesta': 'La primera probabilidad sí es 4/10. Si salió roja y no la devuelves, quedan tres rojas entre nueve bolitas, así que multiplicas 4/10 por 3/9.',
        'segunda': 'Ahh, me faltó quitar una del total también. Entonces sale doce sobre noventa, ¿no?',
        'respuesta_segunda': 'Exacto: 12/90, que se simplifica a 2/15. Son los mismos casos favorables y posibles expresados con números menores.',
        'practica': 'Probé cambiando el ejemplo: si la devolviera, sí quedarían otra vez cuatro rojas de diez.',
        'practica_bot': 'Así es. Comparar los dos casos ayuda a ver por qué cambian las probabilidades cuando hay reposición.',
        'avance': 'Ya pude hacer otro parecido, con dos azules. Me dio seis décimos por cinco novenos.',
        'avance_bot': 'Ese planteamiento respeta que no devuelves la primera. Después puedes multiplicar y simplificar la fracción.',
        'curiosidad': 'Lo de probabilidad suena más interesante con ejemplos de juegos que con puras fórmulas.',
        'curiosidad_bot': 'Los juegos hacen visible qué resultado cuenta y qué cambia en cada intento. Esa intuición también sirve para revisar una fórmula.',
    },
    {
        'area': 'Ciencias Sociales', 'tarea': 'un texto sobre migración interna',
        'detalle': 'Estoy usando un caso de una familia que llega del campo a la ciudad. Tengo que distinguir causas y consecuencias.',
        'detalle_bot': 'Puedes separar las razones para irse de los cambios que ocurren después de llegar. Algunas consecuencias también pueden variar entre familias.',
        'pregunta': 'Buscar trabajo sería una causa. ¿Y que la ciudad crezca, una consecuencia?',
        'respuesta': 'Sí, buscar oportunidades de trabajo puede motivar el traslado. El crecimiento de la población urbana puede ser una consecuencia, junto con otros factores que también influyen.',
        'segunda': 'No quiero escribir que todas las familias llegaron por lo mismo, porque en la lectura hay una que fue por estudios.',
        'respuesta_segunda': 'Esa diferencia vale la pena conservarla. Puedes mostrar dos motivos presentes en la lectura sin generalizarlos a todas las personas.',
        'practica': 'Puse: “En los casos leídos aparecen motivos laborales y educativos, pero las experiencias no son iguales”.',
        'practica_bot': 'La frase distingue los casos y evita una afirmación absoluta. Después puedes añadir el ejemplo de cada familia.',
        'avance': 'Ya separé los dos testimonios del texto. Cada uno muestra una razón distinta para viajar.',
        'avance_bot': 'Así quien lo lea podrá ver de dónde sale cada idea, en lugar de encontrar una lista sin ejemplos.',
        'curiosidad': 'Mi parte favorita de historia es cuando aparecen mapas de cómo eran antes las ciudades.',
        'curiosidad_bot': 'Un mapa permite comparar cambios que a veces pasan desapercibidos en un texto: rutas, barrios y distancias, por ejemplo.',
    },
    {
        'area': 'Ciencia y Tecnología', 'tarea': 'un informe sobre compost',
        'detalle': 'En el colegio tenemos dos recipientes con restos vegetales. Uno quedó mucho más húmedo y hay que comparar lo que observamos.',
        'detalle_bot': 'Puedes empezar por las diferencias que registraron, sin dar por probada una explicación antes de revisar las condiciones de cada recipiente.',
        'pregunta': '¿Puedo decir que más agua siempre hace que el compost se forme más rápido?',
        'respuesta': 'Con esos dos recipientes no conviene afirmar “siempre”. La humedad importa, pero también el aire, el tipo de restos y la temperatura. Describe lo observado y las condiciones que no controlaron.',
        'segunda': 'Entonces diría que vimos una diferencia, pero que faltaría probar si fue por la cantidad de agua.',
        'respuesta_segunda': 'Esa conclusión sí respeta lo que puede mostrar la comparación. Puedes proponer otro ensayo donde mantengan iguales las demás condiciones.',
        'practica': 'Escribí: “Los recipientes mostraron cambios distintos; no podemos atribuirlos solo a la humedad”.',
        'practica_bot': 'Es una forma clara de reconocer el límite del ensayo. Añade después qué registraron en cada recipiente.',
        'avance': 'Ya puse las observaciones por separado y dejé la explicación como una posibilidad.',
        'avance_bot': 'Eso permite distinguir datos e interpretación, que es una parte importante del informe.',
        'curiosidad': 'Me gusta más ciencia cuando hacemos algo con las manos, aunque después toque escribir el informe.',
        'curiosidad_bot': 'La experiencia te da detalles concretos para contar. El informe puede servir para mostrar qué hicieron y qué quedó por averiguar.',
    },
    {
        'area': 'Inglés', 'tarea': 'un párrafo de opinión sobre celulares',
        'detalle': 'Nos pidieron dar una opinión sobre usar el celular en clase, con una razón y un ejemplo.',
        'detalle_bot': 'Puedes elegir una situación concreta y sostener una idea. No necesitas explicar todos los usos posibles del celular en un párrafo.',
        'pregunta': '¿“In my opinion, phones can help us learn” está bien para empezar?',
        'respuesta': 'Sí, es una apertura clara. Después podrías explicar un uso, como consultar una palabra, y dar un ejemplo que apoye tu opinión.',
        'segunda': 'Yo quiero decir que sirve para buscar palabras, pero no para estar viendo videos mientras habla el profe.',
        'respuesta_segunda': 'Puedes expresar esa condición: “Phones can help us look up words, but we should use them for the class activity”. Así tu postura queda más precisa.',
        'practica': 'Puse el ejemplo de buscar una palabra en un diccionario y añadí “for example” antes.',
        'practica_bot': 'Ese conector anuncia bien el ejemplo. Revisa que la oración explique cómo apoya la opinión del comienzo.',
        'avance': 'Ya tengo mi párrafo. Es corto, pero sí tiene opinión, razón y ejemplo.',
        'avance_bot': 'Esas tres partes le dan una estructura que se puede seguir. La extensión puede ajustarse a lo que haya pedido tu docente.',
        'curiosidad': 'A veces reconozco frases de inglés en canciones y recién ahí entiendo para qué eran las clases.',
        'curiosidad_bot': 'Encontrarlas fuera del cuaderno puede hacerlas más fáciles de recordar. También puedes comparar el uso de una frase en distintas canciones.',
    },
    {
        'area': 'Comunicación', 'tarea': 'un comentario sobre un poema',
        'detalle': 'Hay un verso donde la ciudad “despierta”. Tengo que explicar la imagen sin copiar lo que dice el libro.',
        'detalle_bot': 'Puedes explicar qué efecto tiene atribuirle una acción humana a la ciudad y qué detalle del poema apoya tu lectura.',
        'pregunta': '¿Eso sería personificación? Porque una ciudad no duerme de verdad.',
        'respuesta': 'Sí: se presenta a la ciudad como si pudiera despertar. La imagen puede sugerir que empieza el movimiento del día, según el contexto del poema.',
        'segunda': 'Más abajo habla de puertas que se abren y vendedores. Entonces sí se refiere a que empieza la actividad.',
        'respuesta_segunda': 'Esos detalles respaldan esa interpretación. Puedes relacionar la imagen del despertar con esas escenas, sin decir que sea la única lectura posible.',
        'practica': 'Mi explicación quedó así: “El despertar representa el comienzo de la actividad, que aparece en las puertas y los vendedores”.',
        'practica_bot': 'Has unido la imagen con dos elementos del texto. Si citas palabras del poema, conserva las comillas para distinguirlas de tu comentario.',
        'avance': 'Ya añadí el verso al lado de mi explicación. Así se entiende qué parte estoy comentando.',
        'avance_bot': 'Sí, el lector podrá contrastar tu interpretación con el fragmento original.',
        'curiosidad': 'Prefiero los cuentos a los poemas, pero ese al menos tenía imágenes que sí podía imaginar.',
        'curiosidad_bot': 'Puedes entrar al poema por esas imágenes. No hace falta que todos los géneros te gusten por igual para encontrar algo que comentar.',
    },
    {
        'area': 'Desarrollo Personal y Ciudadanía', 'tarea': 'un argumento para un debate',
        'detalle': 'El debate es sobre cuidar las áreas comunes del colegio. Mi ejemplo es lo que pasa con las botellas en el patio.',
        'detalle_bot': 'Ese ejemplo puede ayudarte si explicas qué ocurre y cómo se relaciona con tu postura sobre el cuidado de lo común.',
        'pregunta': '¿Decir “hay que cuidar el patio porque es de todos” alcanza como argumento?',
        'respuesta': 'Expresa una razón general. Puedes desarrollarla: cuando el patio queda sucio, afecta a quienes lo usan y al trabajo de limpieza. Después añade un ejemplo verificable de lo que observaron.',
        'segunda': 'En el recreo dejamos botellas al costado del tacho aunque sí había espacio adentro. Eso sí lo vimos.',
        'respuesta_segunda': 'Puedes usar esa observación sin atribuirle una intención a todo el colegio. Por ejemplo, describe lo que vieron y qué cambio proponen para ese caso.',
        'practica': 'Voy a proponer que cada salón revise el espacio que usó después del recreo, en vez de solo decir “sean limpios”.',
        'practica_bot': 'La propuesta describe una acción observable. En el debate puedes explicar quién la haría y cómo sabrían si ayuda.',
        'avance': 'Ya tengo la postura y el ejemplo. Ahora la propuesta se entiende más que en mi primer borrador.',
        'avance_bot': 'La relación entre el problema observado y la acción propuesta quedó más concreta.',
        'curiosidad': 'Me gustan más los debates cuando alguien da un ejemplo del colegio y no solo lee definiciones.',
        'curiosidad_bot': 'Un ejemplo cercano puede abrir una discusión más concreta. Después se puede relacionar con las ideas generales del tema.',
    },
    {
        'area': 'Educación para el Trabajo', 'tarea': 'el presupuesto de un proyecto',
        'detalle': 'Nuestro ejemplo es vender marcadores de páginas. Tenemos que separar lo que cuesta producirlos de lo que cobraríamos.',
        'detalle_bot': 'Puedes distinguir costo por unidad, precio de venta e ingreso total. Son cantidades relacionadas, pero no significan lo mismo.',
        'pregunta': 'Si hago diez y gasto veinte soles, cada uno me cuesta dos. Si lo vendo a tres, ¿gané treinta?',
        'respuesta': 'Treinta soles sería el ingreso si vendes los diez a tres soles. Al restar los veinte de costo, quedan diez, antes de considerar cualquier otro gasto.',
        'segunda': 'Cierto, estaba usando ingreso y ganancia como si fueran iguales. No habíamos contado el pegamento tampoco.',
        'respuesta_segunda': 'El pegamento también forma parte del costo si lo usan para producirlos. Conviene incluir la porción utilizada y dejar claro cómo la calcularon.',
        'practica': 'Ahora puse una columna de materiales y otra con lo que se usa para los diez marcadores.',
        'practica_bot': 'Esa separación permite revisar de dónde sale el costo del lote. Luego puedes obtener el costo por unidad dividiendo entre diez.',
        'avance': 'El cálculo cambió un poco al sumar el pegamento, pero ya no estamos confundiendo ingreso con ganancia.',
        'avance_bot': 'Es una corrección útil: el presupuesto queda más transparente al incluir los materiales que faltaban.',
        'curiosidad': 'Los marcadores quedaron mejor de lo que creía. Uno tiene un gatito que dibujó alguien del salón.',
        'curiosidad_bot': 'Ese detalle les da identidad. También puede servirles para comentar qué decisiones de diseño tomaron.',
    },
    {
        'area': 'Ciencia y Tecnología', 'tarea': 'un ejercicio de densidad',
        'detalle': 'Tenemos un objeto de ciento veinte gramos y cuarenta centímetros cúbicos. Me toca explicar el procedimiento, no solo el resultado.',
        'detalle_bot': 'Puedes partir de la relación entre masa y volumen. La densidad expresa cuánta masa hay por cada unidad de volumen.',
        'pregunta': 'Divido ciento veinte entre cuarenta y sale tres, pero no sabía qué unidad escribir.',
        'respuesta': 'Con esos datos queda 3 gramos por centímetro cúbico, escrito 3 g/cm³. La unidad sale de dividir la unidad de masa entre la de volumen.',
        'segunda': 'O sea, cada centímetro cúbico tendría tres gramos si el material es uniforme.',
        'respuesta_segunda': 'Sí, esa interpretación funciona para un material uniforme. Has conectado el número y la unidad con su significado.',
        'practica': 'Escribí la división y abajo lo expliqué con mis palabras. Ya no se ve como un tres suelto.',
        'practica_bot': 'La explicación ayuda a comprobar que entiendes qué representa el cálculo.',
        'avance': 'Hice el segundo: doscientos gramos entre cien centímetros cúbicos. Serían dos gramos por centímetro cúbico.',
        'avance_bot': 'Ese cociente y la unidad son correctos para los datos que escribiste.',
        'curiosidad': 'Me acordé de cuando en primaria poníamos cosas en agua para ver cuáles flotaban.',
        'curiosidad_bot': 'Esa experiencia se puede relacionar con la densidad del objeto y la del líquido, cuidando también de qué objeto se trata.',
    },
    {
        'area': 'Matemática', 'tarea': 'una gráfica de funciones',
        'detalle': 'El problema dice que un taxi cobra cinco soles de inicio y dos por cada kilómetro. Tenemos que hacer una tabla y la gráfica.',
        'detalle_bot': 'La tarifa tiene una parte fija y otra que depende de la distancia. Si x representa kilómetros, puedes expresar el costo como 5 + 2x.',
        'pregunta': 'Para cero kilómetros sería cinco y para uno sería siete. ¿La recta empieza en el cinco del eje vertical?',
        'respuesta': 'Sí: cuando x vale cero, el costo es cinco. Por eso la gráfica corta el eje vertical en cinco.',
        'segunda': 'Y al pasar de uno a dos kilómetros sube de siete a nueve. Entonces siempre aumenta dos.',
        'respuesta_segunda': 'Exacto. Ese aumento de dos soles por kilómetro es la pendiente de esta relación lineal.',
        'practica': 'Puse los puntos cero-cinco, uno-siete y dos-nueve. Ya veo por qué quedan en la misma línea.',
        'practica_bot': 'Los tres siguen la misma regla. Al unirlos, conserva la escala de cada eje para representar bien la relación.',
        'avance': 'Me salió otra función cambiando solo la tarifa fija. La línea empieza más arriba, pero sube igual.',
        'avance_bot': 'Así se observa qué cambia con el término fijo y qué se mantiene cuando la pendiente sigue siendo dos.',
        'curiosidad': 'Entiendo mejor una gráfica cuando tiene algo como pasajes o precios y no solo letras.',
        'curiosidad_bot': 'Las situaciones concretas te permiten comprobar qué significa cada eje y si un resultado tiene sentido.',
    },
    {
        'area': 'Ciencias Sociales', 'tarea': 'una comparación de climas',
        'detalle': 'Tengo un gráfico de lluvias de dos ciudades. Una tiene lluvias casi todo el año y la otra concentra casi todo en pocos meses.',
        'detalle_bot': 'Puedes comparar tanto la cantidad como la distribución de las lluvias. Que dos lugares tengan el mismo total anual no implica que llueva igual en cada mes.',
        'pregunta': 'Yo iba a mirar solo la barra más alta, pero entonces no bastaría para decir dónde llueve más en el año.',
        'respuesta': 'Para el total anual necesitas sumar los meses. La barra más alta te dice cuál fue el mes más lluvioso, que responde otra pregunta.',
        'segunda': 'Ya entendí: el máximo mensual y el total del año son dos datos distintos.',
        'respuesta_segunda': 'Sí. Puedes explicar ambos y después describir si las lluvias están repartidas o concentradas.',
        'practica': 'En mi comparación puse primero el total y luego los meses en que se concentra la lluvia.',
        'practica_bot': 'Ese orden permite comparar las mismas características en las dos ciudades.',
        'avance': 'La conclusión cambió: una tenía el mes más lluvioso, pero la otra sumaba más en todo el año.',
        'avance_bot': 'Es un buen ejemplo de por qué conviene revisar qué medida responde a cada pregunta.',
        'curiosidad': 'Me gusta mirar mapas del tiempo, sobre todo cuando sale una parte del Perú que no conozco.',
        'curiosidad_bot': 'Puedes relacionar esos mapas con regiones y estaciones, sin asumir que todos los lugares de una región tienen exactamente el mismo clima.',
    },
    {
        'area': 'Arte', 'tarea': 'un afiche para una actividad del colegio',
        'detalle': 'El afiche tiene un título grande y demasiadas figuras. Nos toca explicar por qué elegimos los colores y el orden.',
        'detalle_bot': 'Puedes pensar en qué debería notar primero quien lo mira y qué información necesita encontrar después.',
        'pregunta': '¿El título puede ser lo más grande aunque el dibujo me haya quedado mejor?',
        'respuesta': 'Sí, si el título comunica lo principal de la actividad. El tamaño puede ayudar a establecer esa prioridad visual, y el dibujo puede acompañarla.',
        'segunda': 'Le bajé el tamaño a dos figuras y ahora sí se ve la fecha. Antes casi ni aparecía.',
        'respuesta_segunda': 'Ese cambio hace más fácil encontrar un dato necesario. Puedes explicar cómo cambió la lectura del afiche al ajustar los tamaños.',
        'practica': 'Dejé solo dos colores de fondo y usé otro para el título. Ya no se mezcla tanto todo.',
        'practica_bot': 'Puedes comparar las dos versiones para mostrar cómo el contraste ayuda a distinguir el título.',
        'avance': 'Guardé las dos versiones del afiche. La diferencia se nota más al verlas juntas.',
        'avance_bot': 'Esa comparación te dará ejemplos concretos cuando expliques tus decisiones de diseño.',
        'curiosidad': 'Me entretiene dibujar letras, por eso siempre termino viendo los letreros de las tiendas.',
        'curiosidad_bot': 'Los letreros muestran muchas maneras de combinar forma y legibilidad. Puedes encontrar ideas incluso en un recorrido habitual.',
    },
)


# Cada episodio relata una misma dificultad dos veces con detalles compatibles.
# Las citas se copian enteras; el estilo puede cambiar el envoltorio del mensaje.
EPISODIOS = {
    'sobrecarga_academica': (
        (
            'Entre el informe de ciencia, la lectura y los ejercicios de mate, siento que son demasiadas tareas juntas para mí.',
            'Son varios trabajos distintos coincidiendo. ¿Cuál de ellos te está resultando más pesado de llevar?',
            'Lo que más me cuesta es pasar de una tarea a otra; todavía me quedan tantas que no logro abarcar todo.',
            'Parece que la cantidad sigue pesando, aunque hayas tocado varias tareas. Podemos mirar una parte concreta, sin exigir resolverlo todo en esta conversación.',
        ),
        (
            'Esta semana se juntaron trabajos de casi todos los cursos y me cuesta hacerme cargo de tanta cosa.',
            'Cuando coinciden trabajos de varios cursos puede resultar difícil abarcar el conjunto. ¿Qué parte necesitas describir primero?',
            'Acabé unas preguntas, pero la cantidad de trabajos que queda sigue siendo más de lo que puedo manejar hoy.',
            'Terminar esas preguntas no hace desaparecer el resto de la carga. Se puede reconocer ese avance y también que todavía es demasiado para un solo día.',
        ),
        (
            'Tengo varias tareas largas a la vez y ya no sé cómo llevar tanta cantidad de trabajo del colegio.',
            'Estás hablando de una carga grande, no de una sola tarea complicada. Podemos empezar por ponerle nombre a lo que se acumuló.',
            'El cuaderno no era tan difícil; lo pesado es que tengo varias entregas grandes encima y siento que no puedo con todas.',
            'Entiendo la diferencia: una actividad puede ser sencilla y aun así el conjunto resultar demasiado. No hace falta minimizarlo porque una parte haya salido.',
        ),
        (
            'En estos días nos han dejado tantos productos de distintos cursos que me siento sobrepasado por la cantidad, así tal cual.',
            'La cantidad de productos es lo que te está sobrepasando. Podemos hablar de eso sin convertirlo en una comparación con lo que hacen los demás.',
            'Todavía me queda bastante; el proyecto, las fichas y la lectura juntos me resultan demasiada carga.',
            'La carga que queda sigue siendo importante para ti. Haber conversado un rato no significa que deba desaparecer esa dificultad.',
        ),
        (
            'Normalmente llevo mis tareas, pero esta vez son demasiados trabajos juntos y me está costando sostenerlos.',
            'Estás notando una diferencia con lo que sueles poder llevar. ¿Qué coincidió esta vez?',
            'Se juntaron dos proyectos además de las tareas de siempre, y esa cantidad extra me sigue pesando.',
            'Eso explica mejor qué cambió: no es solo una tarea nueva, sino una carga extra sobre lo habitual.',
        ),
        (
            'Hay tantas actividades para presentar que por más que haga una siento que no alcanzo a abarcar la cantidad.',
            'La sensación de terminar una y seguir teniendo muchas puede ser agotadora. Podemos distinguir lo que has hecho de lo que todavía se acumuló.',
            'La lista no es el problema por sí sola; de verdad me cuesta hacerme cargo de tantos trabajos al mismo tiempo.',
            'Gracias por aclararlo. Estás señalando la cantidad de trabajo en sí, y eso merece ser tomado en serio.',
        ),
    ),
    'presion_tiempo': (
        (
            'Tengo que entregar una ficha hoy y siento que el tiempo no me alcanza para terminarla antes del cierre.',
            'El plazo está siendo una dificultad concreta. ¿Qué te falta de la ficha?',
            'Todavía voy con el reloj encima por esa entrega; me falta una parte y el cierre sigue igual.',
            'El plazo no cambió y queda trabajo pendiente. Si necesitas consultar una alternativa a tu docente, puedes explicar qué parte está hecha y cuál falta.',
        ),
        (
            'Salí del colegio y ya estoy haciendo cuentas porque tengo muy poco tiempo para la entrega de esta tarde.',
            'Estás sintiendo la entrega muy cerca. Podemos centrarnos en lo que queda, sin dar por hecho que debas hacerlo todo a la vez.',
            'Avancé algo, pero sigo a las carreras porque la hora límite se acerca y aún no termino.',
            'Haber avanzado no elimina esa presión del plazo. Podemos revisar una duda específica que esté frenando la parte pendiente.',
        ),
        (
            'El archivo se recibe hasta hoy y me está faltando tiempo para completarlo como lo pidieron.',
            '¿La dificultad está en alguna parte del contenido o en lo poco que queda hasta el cierre?',
            'Más que no entenderlo, es que me queda muy poco rato para entregar y eso me hace ir apurado.',
            'Gracias por precisar que es el tiempo disponible. Conviene trabajar con ese límite real y evitar exigirte detalles que no se solicitaron.',
        ),
        (
            'No me alcanza la tarde para llegar a la entrega; siento que estoy corriendo detrás de la hora.',
            'La hora de entrega te está marcando el ritmo. Podemos mirar qué parte concreta necesita atención ahora.',
            'Sigo con poco margen antes de enviar, aunque ya tengo una parte. Es el plazo lo que me está apurando.',
            'Sí, la presión sigue vinculada al plazo. Si el tiempo no permite completar lo pedido, hablarlo con tu docente puede ser una opción.',
        ),
        (
            'Esta vez el tiempo entre que salimos y el cierre es muy corto para mí; me falta rato para entregar.',
            'Ese margen corto te está dificultando la entrega. ¿Qué es lo que aún no has podido completar?',
            'Me faltan dos partes y cada vez queda menos tiempo para enviarlo; sigo sintiendo esa prisa.',
            'Son dos partes pendientes con un plazo que se acerca. Podemos abordar una duda de una de ellas, manteniendo claro ese límite.',
        ),
        (
            'Me está costando llegar a la hora de entrega, siento que cada minuto cuenta y no me alcanza.',
            'La falta de tiempo se siente muy presente. Puedes contarme qué queda sin tener que resolverlo todo de golpe.',
            'Aunque hice una parte, todavía tengo el tiempo justo y sigo sin llegar a cerrar la entrega.',
            'La entrega sigue abierta y el margen es justo. Es válido reconocerlo y comunicarlo si necesitas una alternativa.',
        ),
    ),
    'sintomas_fisicos': (
        (
            'Cuando llevo un rato con los trabajos del colegio me empieza a doler la cabeza; ya me pasó varias tardes.',
            'Gracias por contarlo. Ese dolor merece atención, sin asumir una causa solo por el chat. Si sigue o se repite, cuéntaselo a una persona adulta de confianza y busca orientación de salud.',
            'La molestia de cabeza me vuelve cuando paso otro rato con las tareas; no se ha ido del todo.',
            'Entonces la molestia continúa. Puedes hacer una pausa de la pantalla y avisar a una persona adulta; si es intensa o empeora, busca atención médica.',
        ),
        (
            'Por darle vueltas a cosas del colegio me cuesta dormir y al día siguiente siento el cuerpo cansado.',
            'Estás contando que el sueño y el cansancio se relacionan, para ti, con lo que pasa en el colegio. Si esto se repite, sería bueno hablarlo con una persona adulta que pueda acompañarte.',
            'Todavía noto el cansancio de haber dormido poco por quedarme con las tareas en la cabeza.',
            'El cansancio sigue ahí, aunque puedas conversar o hacer algo. No necesitas tratarlo como falta de ganas; si persiste, busca apoyo de una persona adulta y orientación de salud.',
        ),
        (
            'A veces, cuando estoy con las tareas, se me pone el cuello muy tenso y termino con dolor.',
            'Esa tensión con dolor merece cuidado. Una pausa y cambiar de postura pueden resultar cómodos, pero no reemplazan una evaluación si sigue pasando.',
            'El cuello todavía está tenso después de trabajar otro rato en el cuaderno.',
            'Gracias por volver a mencionarlo. No conviene forzarte a seguir con dolor; avisa en casa y pide orientación si continúa o aumenta.',
        ),
        (
            'Antes de algunas actividades del colegio me molesta la barriga; me pasa justo cuando pienso en lo que tengo que presentar.',
            'Puedes contar esa relación que has notado sin que aquí demos por confirmada una causa. Si la molestia se repite, una persona adulta y un profesional de salud pueden ayudarte a revisarla.',
            'La barriga me volvió a molestar al retomar lo del colegio; por eso dejé un rato el cuaderno.',
            'Hiciste una pausa porque apareció de nuevo. Coméntalo en casa; si el dolor es intenso, persiste o empeora, necesita atención de salud.',
        ),
        (
            'Estas noches, pensando en los estudios, me despierto varias veces y luego amanezco con cansancio físico.',
            'Dormir entrecortado puede afectar cómo te sientes durante el día. Conviene que una persona adulta de confianza sepa que está ocurriendo, sobre todo si se repite.',
            'Hoy sigo con el cuerpo pesado por esas noches de sueño cortado cuando me quedo pensando en el colegio.',
            'Lo que cuentas no se resuelve necesariamente con una conversación. Busca acompañamiento en casa y orientación de salud si continúa.',
        ),
        (
            'Después de estar pendiente de los trabajos siento los hombros duros y me duelen; lo vengo notando estos días.',
            'La molestia es algo que puedes comunicar en casa. Puedes descansar un momento de la actividad, y si persiste conviene que la revise un profesional.',
            'Los hombros siguen tensos al volver a los trabajos. No es solo que quiera dejar el cuaderno, sí me duelen.',
            'Te creo cuando dices que hay dolor. No hace falta justificarlo como si fuera una excusa; cuéntaselo a una persona adulta y busca atención si sigue o empeora.',
        ),
    ),
    'sintomas_psicologicos': (
        (
            'Me pongo muy nervioso cuando pienso que tengo que exponer delante del salón, aunque conozca el tema.',
            'Conocer el tema y sentir nervios pueden ocurrir juntos. ¿Qué momento de la exposición te viene a la cabeza?',
            'Sigo imaginando que me voy a quedar en blanco al exponer y eso me mantiene preocupado.',
            'Esa preocupación sigue apareciendo. Si quieres, puedes ensayar una frase de inicio; no sería una obligación ni una garantía de quitar los nervios.',
        ),
        (
            'Últimamente me preocupa bastante equivocarme en clase; incluso después me quedo pensando en lo que dije.',
            'Quedarte repasando lo que dijiste puede hacer pesada una situación que ya terminó. Podemos hablar de un ejemplo sin juzgarte por equivocarte.',
            'Todavía le doy vueltas a una respuesta del salón y me cuesta concentrarme en la tarea por esa preocupación.',
            'La preocupación está interfiriendo con esta tarea. Si te ocurre seguido o te hace sentir muy mal, puedes buscar acompañamiento de una persona adulta o del área de orientación del colegio.',
        ),
        (
            'Con cosas del colegio ando muy irritable; cualquier error del trabajo me molesta más de lo normal.',
            'Estás notando irritación en situaciones escolares. ¿Hay algún momento concreto que quieras contar?',
            'Hoy borré una parte que estaba mal y otra vez me dio mucha cólera por lo del trabajo.',
            'Ese error volvió a activar la molestia. Puedes parar un momento antes de continuar; si esto se mantiene, hablarlo con alguien de confianza puede ayudarte a encontrar acompañamiento.',
        ),
        (
            'Cuando pienso en las evaluaciones del colegio me preocupo tanto que luego leo la misma línea y no me concentro.',
            'La preocupación está apareciendo mientras intentas leer. Podemos mirar una parte pequeña del texto y también reconocer que eso no resuelve por sí solo cómo te sientes.',
            'Me pasa de nuevo: estoy leyendo, pero me quedo pensando en la evaluación y pierdo el hilo.',
            'Gracias por explicar cómo ocurre. Si esa preocupación sigue interrumpiendo tus actividades, sería bueno hablarlo con una persona adulta o con orientación del colegio.',
        ),
        (
            'Me da bastante tristeza sentir que no me sale lo del colegio como esperaba, y me quedo pensando en eso.',
            'Lamento que te esté haciendo sentir así. Un resultado escolar no define todo lo que eres; puedes contar lo que pasó sin tener que restarle importancia.',
            'Esa tristeza por mis resultados sigue ahí, aunque hoy haya podido hacer un ejercicio.',
            'Hacer un ejercicio no obliga a que desaparezca la tristeza. Si continúa o te cuesta llevarla, busca una persona adulta de confianza que pueda acompañarte.',
        ),
        (
            'En las actividades del colegio me comparo mucho y termino con ansiedad por si todos lo hicieron mejor que yo.',
            'Esa comparación te está haciendo sentir mal. Podemos centrarnos en una situación concreta, sin usar a tus compañeros como medida de tu valor.',
            'Todavía me viene la preocupación de que mi trabajo sea el peor del salón, aunque no haya visto los otros.',
            'Estás reconociendo que esa idea aparece sin haber visto los otros trabajos. Si la preocupación se repite y pesa mucho, busca apoyo de una persona adulta u orientación del colegio.',
        ),
    ),
}


APOYOS = {
    'planificacion': (
        (
            'Hoy anoté los trabajos que tengo y los separé por lo que pide cada curso. Eso sí lo estoy usando para organizarme.',
            'Has puesto en práctica una forma de organizar el trabajo. ¿Te está sirviendo tener visibles esas partes?',
            'Volví a mi lista y marqué la parte que ya hice; también cambié el orden de dos tareas según lo que faltaba.',
            'Estás ajustando una herramienta que ya usas. Puedes mantenerla sencilla para que te ayude en vez de añadir otra obligación.',
        ),
        (
            'Me hice un horario de estudio para hoy, con ratos separados para cada tarea; lo tengo al lado del cuaderno.',
            'Ese horario es una acción concreta que ya pusiste en marcha. Puede tener margen si una actividad tarda distinto de lo esperado.',
            'Revisé el horario y moví un bloque porque esa tarea necesitó más rato. No lo dejé tal cual si ya no servía.',
            'Adaptarlo a lo que ocurrió forma parte de usarlo. Un horario puede orientar sin tener que cumplirse al minuto.',
        ),
        (
            'Para estudiar uso una hoja con tres partes: lo que falta, lo que estoy haciendo y lo que ya quedó.',
            'Esa separación te permite ver el estado de cada actividad sin tener que recordarlo todo.',
            'Ya pasé una actividad a la parte de terminado y dejé escrita la siguiente en mi hoja.',
            'La hoja refleja un cambio concreto. Puedes seguir usándola si te ayuda a ubicar lo que queda.',
        ),
        (
            'Esta semana he usado la agenda para repartir mis tareas entre distintos ratos; hoy también la abrí antes de empezar.',
            'Estás usando la agenda en la práctica, no solo pensando en hacerlo. ¿Qué información te resulta más útil tener ahí?',
            'Añadí en mi agenda los pasos que faltan del trabajo y dejé espacio para una pausa.',
            'Has concretado los pasos y también un descanso. La agenda puede seguir siendo flexible si cambia algo.',
        ),
        (
            'Divido las tareas largas en partes y las escribo en una nota. Hoy empecé con una de esas partes.',
            'Convertiste una tarea amplia en partes visibles y ya empezaste una. Eso permite saber con más precisión qué estás haciendo.',
            'La nota me sirvió para dejar marcado hasta dónde llegué y qué parte queda después.',
            'Ese registro puede facilitar retomar más tarde sin reconstruir todo de memoria.',
        ),
    ),
    'automotivacion': (
        (
            'Cuando estudio me recuerdo que quiero terminar bien quinto; decirme eso me ayuda a seguir con mis actividades.',
            'Estás usando una meta personal para sostener el esfuerzo. Puede convivir con reconocer que hay días distintos.',
            'Hace un rato me repetí que no necesito hacerlo perfecto para seguir aprendiendo, y volví a intentar el ejercicio.',
            'Te hablaste de una manera que te permitió volver a intentarlo. Ese esfuerzo concreto cuenta, aunque el resultado todavía no esté listo.',
        ),
        (
            'Para seguir estudiando me digo que puedo avanzar de a poco. No es frase del profe; me lo repito yo.',
            'Es una forma propia de darte ánimo. Puedes reconocer lo que haces sin exigirte sentir entusiasmo todo el tiempo.',
            'Me salió una parte y me lo reconocí en vez de decir que no cuenta porque falta el resto. Eso me dio ganas de continuar.',
            'Reconocer una parte terminada puede ayudarte a sostener el esfuerzo sin borrar lo que aún falta.',
        ),
        (
            'Cuando un ejercicio no sale a la primera, me recuerdo otros que sí aprendí y eso me anima a probar otra vez.',
            'Estás recurriendo a experiencias propias para darte ánimo. Puedes probar otra vez sin convertir un error en una opinión sobre toda tu capacidad.',
            'Me acordé de un tema que antes tampoco entendía y me dije que podía seguir practicando este.',
            'Esa comparación con tu propio aprendizaje te sirvió para mantener el intento. No necesitas compararte con el ritmo de otra persona.',
        ),
        (
            'Me animo a estudiar pensando en la carrera que me gustaría conocer después del cole. Hoy usé eso para empezar.',
            'Esa posibilidad de futuro te sirve como motivo personal. No tienes que tener toda tu decisión tomada para que te anime hoy.',
            'Me volví a decir por qué quiero acabar bien el colegio y seguí con la actividad que había empezado.',
            'Estás conectando una tarea de hoy con algo que te importa. También puedes dejar espacio para descansar.',
        ),
        (
            'Yo me doy ánimo diciendo que un error no cancela lo que ya aprendí. Lo hago cuando estoy con las tareas.',
            'Esa manera de hablarte reconoce el error sin reducir todo tu aprendizaje a él.',
            'En el cuaderno me salió mal una parte y me dije “puedo corregir esto”. Así seguí intentándolo.',
            'Te diste permiso para corregir y continuar. Es una acción más concreta que exigirte que todo salga de una vez.',
        ),
    ),
    'busqueda_soporte': (
        (
            'Le pedí a mi profe que me explicara una parte de la tarea que no entendía, y sí me aclaró ese paso.',
            'Pediste una aclaración concreta y recibiste ayuda. ¿Qué parte quedó más clara después?',
            'Le mandé otra consulta corta a la profe sobre la indicación que faltaba. Ya me respondió qué había que presentar.',
            'La consulta te permitió aclarar la indicación con quien la dio. Puedes distinguir eso de las partes que aún necesitas hacer por tu cuenta.',
        ),
        (
            'Ayer le pedí a un compañero que me explicara cómo había entendido la consigna; me ayudó a ver qué pedían.',
            'Compartir cómo entendieron la consigna puede aclarar el comienzo, manteniendo que cada quien haga su trabajo.',
            'Hoy volví a consultar a ese compañero una duda del enunciado. Me mostró qué parte del texto había que mirar.',
            'Esa ayuda se centró en entender el enunciado. Después puedes elaborar tu propia respuesta con esa aclaración.',
        ),
        (
            'En casa le pedí a mi hermana que escuchara una parte de mi exposición y me dijera qué no se entendía.',
            'Buscaste una opinión sobre cómo se escucha tu explicación. Puede darte información distinta de leerla en silencio.',
            'Le volví a leer la parte corregida a mi hermana y me dijo qué frase se entendía mejor.',
            'Tuviste una devolución sobre una parte específica. Puedes decidir qué cambio te sirve conservar.',
        ),
        (
            'Le conté a mi mamá que necesitaba ayuda para entender las indicaciones del trabajo y las leyó conmigo.',
            'Pudiste pedir acompañamiento para revisar las indicaciones. Eso no quita que las ideas y el trabajo puedan ser tuyos.',
            'Fui a preguntarle de nuevo a mi mamá por una palabra de la consigna y la revisamos juntos.',
            'La ayuda fue concreta y te permitió aclarar esa palabra. Puedes seguir con tu propia explicación a partir de ahí.',
        ),
        (
            'Le pedí al tutor un momento para hablar de cómo me está yendo con los estudios, y me escuchó.',
            'Has buscado un espacio de acompañamiento con alguien del colegio. Puedes contar a tu ritmo qué parte de esa conversación te sirvió.',
            'Le volví a escribir al tutor para pedirle orientación con una duda del colegio; ya acordamos cuándo conversar.',
            'Quedó un siguiente contacto concreto. No necesitas esperar a tener todo resuelto para volver a hablar con él.',
        ),
    ),
}


PASATIEMPOS = (
    ('fútbol', 'Me gusta jugar de lateral. Corro bastante, aunque hacer goles no es lo mío jaja.', 'Cada posición aporta algo distinto. ¿Te divierte más marcar o salir jugando?', 'Salir jugando, pero a veces intento un pase largo y termina lejísimos.', 'Esas jugadas también dejan anécdotas. Puedes disfrutar el partido sin que cada pase salga perfecto.'),
    ('dibujar', 'En mis hojas siempre termino dibujando caritas y letras, incluso cuando el dibujo era para otra cosa.', 'Parece una forma tuya de llenar la hoja. ¿Te gusta más inventar personajes o copiar algo que ves?', 'Inventar personajes. Tengo uno con una mochila enorme, no sé por qué siempre lo dibujo así.', 'Ese detalle puede volverse parte del personaje. No necesitas tener una explicación cerrada para disfrutar inventándolo.'),
    ('escuchar música', 'Escucho de todo un poco, pero repito la misma canción hasta que ya todos en casa se la saben.', 'A veces una canción se queda una temporada. ¿Te llama más la letra o cómo suena?', 'Primero cómo suena, después recién me fijo en la letra. A veces era otra cosa nada que ver.', 'Descubrir la letra después puede cambiar cómo la escuchas. También hay canciones que se disfrutan por el ritmo.'),
    ('vóley', 'Me gusta recibir la pelota; sacar todavía me sale medio chueco.', 'La recepción también exige práctica. ¿Tienen alguna jugada que les guste intentar?', 'Solo tratamos de hacer los tres toques, pero cuando sale celebramos como si fuera campeonato.', 'Es un buen momento compartido cuando una jugada que estaban intentando sí sale.'),
    ('cocinar algo sencillo', 'A veces hago pan con huevo, pero me entretengo poniéndole lo que encuentre para que no sea siempre igual.', 'Hay bastante espacio para probar en algo sencillo. ¿Tienes una combinación favorita?', 'Con tomate y un poco de queso. Una vez le puse demasiada sal y nadie quiso repetir.', 'Esas pruebas también enseñan qué ajustar. La combinación con tomate y queso suena a una que sí quisiste repetir.'),
    ('ver películas', 'Prefiero las películas de misterio, las que te dejan pensando quién sabía qué.', '¿Te gusta intentar resolverlo antes o dejarte sorprender por el final?', 'Siempre digo que ya sé quién fue y luego resulta que no era. Igual me divierte.', 'Intentar adivinar puede ser parte de la diversión, aunque el final te cambie la idea.'),
    ('leer historietas', 'Me gustan las historietas con viñetas sin texto; a veces cuentan un montón solo con una cara.', 'Ahí el dibujo lleva gran parte de la narración. ¿Te fijas primero en el personaje o en todo lo que pasa alrededor?', 'En las caras, después vuelvo a mirar el fondo y encuentro algo que no había visto.', 'Esa segunda mirada puede cambiar la escena. Es una forma interesante de seguir una historia.'),
    ('tomar fotos', 'Le tomo fotos al cielo cuando cambia de color. Tengo un montón casi iguales en el celular.', 'En fotos parecidas a veces se notan cambios pequeños. ¿Hay algún color que busques más?', 'Los naranjas, pero en la foto siempre se ven distintos a como estaban de verdad.', 'La cámara y la luz pueden cambiar lo que registra. Aun así, cada imagen guarda algo de ese momento.'),
    ('bailar', 'Me sé pedazos de canciones, no una coreografía entera. Si cambian de parte ya me pierdo jaja.', 'Puedes disfrutar esos pedazos sin tener que aprender una coreografía completa. ¿Te gusta inventar pasos también?', 'Sí, aunque después no me acuerdo qué hice y nunca lo repito igual.', 'A veces lo divertido está justamente en probar algo que sale distinto cada vez.'),
    ('jugar ajedrez', 'Yo hago la apertura más o menos y después ya invento. A veces me comen la reina por distraerme mirando otra pieza.', 'En ajedrez mirar una amenaza puede hacer que pase otra desapercibida. ¿Te gustan las partidas cortas o con tiempo para pensar?', 'Con tiempo, así puedo mirar el tablero completo. Las rápidas se acaban antes de que entienda qué pasó.', 'Ese ritmo te deja explorar más las posiciones. Puedes elegir el tipo de partida que disfrutas.'),
    ('andar en bicicleta', 'Me gusta salir un rato en bicicleta por donde hay poco tránsito. Siempre termino dando una vuelta más.', '¿Te gusta recorrer el mismo camino o encontrar uno distinto?', 'Casi siempre el mismo, ya sé dónde cambia el piso y dónde hay que ir más lento.', 'Conocer el recorrido permite notar esos detalles. Sigue cuidando el tránsito y usando protección.'),
    ('armar cosas de papel', 'Hago figuras de papel cuando tengo una hoja suelta. La grulla todavía me sale deforme.', 'Los pliegues pequeños pueden cambiar mucho una figura. ¿Hay alguna que ya te salga como quieres?', 'El barquito sí, ese me lo enseñaron hace años y no se me olvida.', 'Ese ya quedó en tus manos. La grulla puede seguir siendo una figura para experimentar.'),
)


RELLENO = (
    ('En mi salón, cuando toca leer un diálogo, siempre alguien termina haciendo voz de narrador de película.', 'Esos cambios de voz pueden volver distinta una lectura. ¿A ti te gusta participar o prefieres escuchar?'),
    ('Me gusta cuando una clase usa fotos antiguas del barrio. Reconozco las calles aunque todo esté distinto.', 'Es una manera cercana de observar cambios. Una misma calle puede mostrar bastante historia en sus detalles.'),
    ('Hoy alguien encontró una regla que llevaba días buscando y estaba adentro de su propio libro.', 'Es de esas cosas que se buscan por todos lados y aparecen en el lugar más cercano.'),
    ('En el recreo hablaron de la foto de la promoción. Todavía no decidimos ni cómo nos vamos a poner.', 'Es un recuerdo que suele dar para bastantes ideas. ¿Quieren algo formal o más parecido a cómo son en el salón?'),
    ('El salón tiene un mural con dibujos de todos. El mío quedó casi escondido detrás del título.', 'Aunque se vea menos, forma parte del conjunto. ¿Qué habías dibujado?'),
    ('Me gustan los trabajos donde puedes elegir el ejemplo. Termino entendiendo mejor si uso algo que conozco.', 'Elegir un ejemplo cercano puede ayudarte a explicar una idea con detalles propios.'),
    ('El otro día cambiaron las carpetas de sitio y todos caminábamos al lugar de antes por costumbre.', 'Las rutinas se notan mucho cuando cambia algo pequeño del espacio.'),
    ('Hay una ventana del salón por donde se ve una pared llena de plantas. De lejos parece un jardín colgado.', 'Es un detalle particular del lugar. A veces un mismo espacio tiene cosas que uno empieza a notar después.'),
    ('En la clase de arte mezclamos colores y el mío quedó de un tono que nadie supo cómo llamar.', 'Los colores intermedios suelen dar para inventar nombres. También puedes anotar la mezcla si quieres volver a obtenerlo.'),
    ('A veces los ejemplos de los libros tienen unos nombres que nadie en el salón usa y nos da risa.', 'Los ejemplos se sienten distintos cuando se parecen más a lo que conocen. Puedes cambiar los nombres sin cambiar la idea del ejercicio.'),
    ('La palabra que más salió hoy fue “sustenta”. La dijeron en varios cursos, cada uno con un ejemplo distinto.', 'En general invita a mostrar en qué se apoya una idea. El tipo de respaldo cambia según la actividad.'),
    ('Me quedé viendo cómo se reflejan las letras en una botella. Se ven al revés dependiendo de dónde la mires.', 'Es una observación curiosa. La forma del recipiente y el agua pueden cambiar cómo pasa la luz.'),
    ('En quinto ya tenemos varias anécdotas del mismo salón. Una palabra cualquiera y todos se acuerdan de algo.', 'Con el tiempo se forma una especie de historia compartida del grupo.'),
    ('Creo que se me quedó un lapicero en el bolsillo de la casaca. Siempre aparece uno cuando ya saqué otro.', 'Los bolsillos a veces funcionan como un segundo estuche. Al menos apareció antes de terminar la tarde.'),
    ('Hay cursos que me gustan más por el tipo de actividad que por el nombre del curso.', 'Tiene sentido fijarte en cómo aprendes o participas. Dentro de un curso puede haber actividades muy distintas.'),
    ('Hoy el cielo se veía clarito al salir del colegio y luego se llenó de nubes. Cambió bastante rápido.', 'Es de esos detalles que dan otra sensación al mismo recorrido. Puedes observarlo sin que tenga que convertirse en una tarea.'),
    ('En la biblioteca encontré un libro con anotaciones antiguas en lápiz. No entendí quién las había hecho.', 'Es una pequeña huella de otras lecturas. Si es un libro prestado, lo mejor es conservarlo sin añadir marcas.'),
    ('Una vez tuvimos que describir un objeto sin decir su nombre. Con mi explicación nadie adivinó que era una taza.', 'A veces la descripción destaca detalles que otros no asocian con el objeto. También es una forma de mirar lo habitual de otra manera.'),
    ('Me gusta cuando dejan comparar dos respuestas y explicar por qué una se entiende mejor.', 'Comparar explicaciones permite mirar el razonamiento, además del resultado.'),
    ('El cuaderno que uso tiene las primeras páginas muy ordenadas y al final ya salen dibujos en los márgenes.', 'Los cuadernos también van mostrando cómo se usaron durante el año.'),
)


def _contexto_numerico(indice, rng):
    """Casos nuevos con relaciones y resultados calculados, no números sueltos."""
    tipo = indice % 5
    if tipo == 0:
        rojas, azules = rng.randint(3, 9), rng.randint(4, 11)
        total = rojas + azules
        f = Fraction(rojas * (rojas - 1), total * (total - 1))
        return {
            'area': 'Matemática', 'tarea': 'un problema de sacar fichas de una bolsa',
            'detalle': f'Tengo una bolsa con {rojas} fichas rojas y {azules} azules. En el problema sacan dos sin devolverlas y preguntan por dos rojas.',
            'detalle_bot': 'Al no devolver la primera, cambian tanto las fichas que quedan del color como el total. Puedes seguir las dos extracciones por separado.',
            'pregunta': f'En la primera hay {rojas} de {total}. ¿En la segunda también uso {total} abajo?',
            'respuesta': f'Si salió una roja y no la devuelves, quedan {rojas - 1} rojas entre {total - 1} fichas. Para dos rojas multiplicas {rojas}/{total} por {rojas - 1}/{total - 1}.',
            'segunda': f'Entonces tendría {rojas * (rojas - 1)} sobre {total * (total - 1)} antes de simplificar. Ya entendí por qué se quita una en los dos sitios.',
            'respuesta_segunda': f'Sí. Esa fracción se puede escribir como {f.numerator}/{f.denominator}. En cada paso estás usando las fichas que realmente quedan.',
            'practica': f'Escribí al lado “sin devolución” para explicar por qué pasa de {total} a {total - 1}.',
            'practica_bot': 'Esa aclaración une el cálculo con la condición del problema. Así se puede seguir el procedimiento, no solo el resultado.',
            'avance': f'Ahora probé el caso con devolución: la segunda vez sí serían otra vez {rojas} rojas de {total}.',
            'avance_bot': 'Exacto, al devolver la primera se recupera la composición inicial de la bolsa.',
            'curiosidad': 'En clase lo hicieron con papeles de colores y se entendía más que cuando lo veía solo escrito.',
            'curiosidad_bot': 'Ver cómo cambia lo que queda en la bolsa puede dar sentido a las fracciones del problema.',
        }
    if tipo == 1:
        volumen, densidad = rng.choice((20, 25, 30, 40, 50)), rng.choice((2, 3, 4, 5))
        masa = volumen * densidad
        return {
            'area': 'Ciencia y Tecnología', 'tarea': 'una ficha sobre masa y volumen',
            'detalle': f'En mi ficha el objeto tiene {masa} gramos y un volumen de {volumen} centímetros cúbicos. Piden la densidad y una explicación.',
            'detalle_bot': 'La densidad relaciona la masa con el volumen. Puedes dividir esas dos cantidades y conservar sus unidades.',
            'pregunta': f'Me salió {densidad}, pero si escribo solo el número parece que no estoy diciendo de qué es.',
            'respuesta': f'Con los datos que tienes, la densidad es {densidad} g/cm³. La unidad significa gramos por cada centímetro cúbico.',
            'segunda': f'O sea que, si fuera uniforme, {2 * volumen} centímetros cúbicos del mismo material tendrían {2 * masa} gramos.',
            'respuesta_segunda': 'Sí, para el mismo material uniforme se mantiene esa relación. Al duplicar el volumen también se duplica la masa.',
            'practica': f'Dejé la operación {masa} dividido entre {volumen} y añadí la unidad después del resultado.',
            'practica_bot': 'Así quedan visibles tanto los datos como el significado del cociente.',
            'avance': f'Lo comprobé multiplicando {densidad} por {volumen} y volví a los {masa} gramos del inicio.',
            'avance_bot': 'Esa comprobación es coherente: densidad por volumen recupera la masa en este caso.',
            'curiosidad': 'Nunca me había fijado en que objetos igual de grandes pueden pesar distinto.',
            'curiosidad_bot': 'La densidad ayuda a describir justamente esa diferencia entre materiales.',
        }
    if tipo == 2:
        fijo, variable = rng.randint(3, 9), rng.randint(2, 5)
        return {
            'area': 'Matemática', 'tarea': 'una tabla de costos de un recorrido',
            'detalle': f'El ejemplo cobra {fijo} soles al inicio y {variable} por cada kilómetro. Nos pidieron explicar la tabla, no solo llenarla.',
            'detalle_bot': 'Hay un costo que no depende de los kilómetros y otro que aumenta con la distancia. Puedes escribir esa relación como una función.',
            'pregunta': f'Para cero kilómetros puse {fijo}, para uno {fijo + variable} y para dos {fijo + 2 * variable}. ¿Está bien aunque el primero no sea cero?',
            'respuesta': f'Sí. El cobro inicial es {fijo}, por eso el costo no parte de cero. Si x son kilómetros, la expresión es {fijo} + {variable}x.',
            'segunda': f'Entonces lo que sube igual en cada paso es {variable}. El {fijo} solo cambia desde dónde empieza.',
            'respuesta_segunda': 'Lo has distinguido bien: el aumento por kilómetro es la pendiente y el cobro inicial fija el corte con el eje vertical.',
            'practica': f'Dibujé tres puntos con esos datos y escribí “costo en soles” en el eje de arriba.',
            'practica_bot': 'Puedes llamarlo eje vertical para identificarlo con claridad. El otro eje muestra los kilómetros recorridos.',
            'avance': f'Para tres kilómetros me salió {fijo + 3 * variable}; sigue aumentando de {variable} en {variable}.',
            'avance_bot': 'Ese resultado sigue la misma regla de la tabla y de la expresión.',
            'curiosidad': 'Con precios me resulta más fácil saber qué significa cada letra de una función.',
            'curiosidad_bot': 'El contexto te permite interpretar el número y comprobar si la relación tiene sentido.',
        }
    if tipo == 3:
        costo, precio, cantidad = rng.randint(2, 6), rng.randint(8, 12), rng.choice((8, 10, 12, 15))
        return {
            'area': 'Educación para el Trabajo', 'tarea': 'un cálculo para un puesto escolar',
            'detalle': f'En el ejemplo hacemos {cantidad} llaveros; producir cada uno cuesta {costo} soles y el precio sería {precio}.',
            'detalle_bot': 'Puedes calcular por separado cuánto cuesta el lote y cuánto ingresarías si vendieras todas las unidades.',
            'pregunta': f'Multipliqué {cantidad} por {precio} y me dio {cantidad * precio}. ¿Eso sería todo lo que ganamos?',
            'respuesta': f'Es el ingreso por las ventas. El costo de producirlos es {cantidad * costo}; la diferencia sería {cantidad * (precio - costo)}, antes de otros gastos que no estén incluidos.',
            'segunda': f'Ah, no había restado los {cantidad * costo}. Ingreso y ganancia no eran lo mismo.',
            'respuesta_segunda': 'Exacto. Distinguirlos permite explicar de dónde sale cada cantidad del presupuesto.',
            'practica': f'Dejé una fila para ingreso y otra para costo. Al final resté {cantidad * precio} menos {cantidad * costo}.',
            'practica_bot': 'Ahora se puede revisar qué se está restando y por qué. Conviene indicar qué materiales ya incluye ese costo.',
            'avance': f'El resultado quedó en {cantidad * (precio - costo)} soles, suponiendo que sí vendemos los {cantidad}.',
            'avance_bot': 'Y has conservado una condición importante: ese resultado depende de vender la cantidad prevista.',
            'curiosidad': 'Me gusta imaginar cómo quedaría el puesto, sobre todo el cartel de precios.',
            'curiosidad_bot': 'Ese cartel puede conectar la parte de diseño con los datos que están calculando.',
        }
    a, b, c = rng.choice((10, 12, 14, 16)), rng.choice((10, 12, 14, 16)), rng.choice((12, 14, 16, 18))
    d = (4 - (a + b + c) % 4) % 4 + 12
    promedio = (a + b + c + d) // 4
    return {
        'area': 'Matemática', 'tarea': 'un ejemplo de promedios',
        'detalle': f'El ejemplo trae las notas {a}, {b}, {c} y {d}. Son datos de una ficha, no mis notas.',
        'detalle_bot': 'Si las cuatro notas tienen el mismo peso, el promedio se obtiene sumándolas y dividiendo entre cuatro.',
        'pregunta': f'La suma me dio {a + b + c + d}. ¿La divido entre cuatro aunque una nota se repita?',
        'respuesta': f'Sí. Cada nota corresponde a un dato y se cuenta, aunque dos valores coincidan. Aquí el promedio es {promedio}.',
        'segunda': f'Entonces sería como repartir el total {a + b + c + d} en cuatro partes iguales.',
        'respuesta_segunda': 'Esa es una interpretación útil de la media aritmética cuando todos los datos tienen el mismo peso.',
        'practica': f'Escribí el promedio {promedio} y aclaré que son cuatro datos del mismo peso.',
        'practica_bot': 'La aclaración muestra qué condición estás usando para calcularlo de esa manera.',
        'avance': 'Después vi otro ejercicio que sí tiene pesos distintos. Ese ya no se haría igual.',
        'avance_bot': 'Correcto: en un promedio ponderado se tiene en cuenta el peso de cada dato. Puedes revisar qué porcentaje o peso indica ese nuevo ejercicio.',
        'curiosidad': 'Pensaba que promedio era solo usar una fórmula, pero ahora entiendo la idea de repartir.',
        'curiosidad_bot': 'Esa interpretación permite revisar si el resultado es razonable antes de quedarte únicamente con la operación.',
    }


def _episodio_contextual(indicador, contexto, rng):
    """Relatos con detalles concretos distintos, manteniendo el mismo indicador."""
    curso = contexto['area'].lower()
    trabajo = contexto['tarea']
    if indicador == 'sobrecarga_academica':
        tarea_a, tarea_b = rng.sample((
            'un resumen de cuatro páginas', 'dos fichas de lectura',
            'una maqueta con su explicación', 'un audio en inglés',
            'un informe del experimento', 'una presentación de ocho diapositivas',
            'un comentario de un cuento', 'tres páginas de ejercicios',
            'un afiche con su sustento', 'un cuadro comparativo de historia',
        ), 2)
        primero = rng.choice((
            f'Aparte de {trabajo}, tengo {tarea_a} y {tarea_b}; toda esa cantidad de trabajos del cole me está sobrepasando.',
            f'Se me juntaron {tarea_a}, {tarea_b} y lo de {curso}. Son demasiadas actividades a la vez para mí.',
            f'Lo pesado de estos días es la cantidad: entre {tarea_a} y {tarea_b}, más lo de {curso}, me cuesta abarcar tantas tareas.',
        ))
        luego = rng.choice((
            f'Terminé una parte, pero todavía están {tarea_a} y {tarea_b}; la cantidad de trabajo sigue siendo demasiado para mí.',
            f'Volví a mirar los trabajos y lo de {curso} es solo una parte. Me sigue costando llevar tantas actividades juntas.',
            f'No es una sola pregunta difícil: siguen pendientes {tarea_b} y otros trabajos, y siento que esa cantidad me supera.',
        ))
        respuesta = rng.choice((
            f'No es solo {trabajo}, sino varias actividades coincidiendo. Podemos reconocer esa cantidad y revisar una parte concreta sin pedirte resolver todo de golpe.',
            f'Lo de {curso} es una parte de una carga que se acumuló. ¿Quieres describir qué es lo más pesado de esa cantidad?',
            'Por lo que cuentas, el conjunto se siente mayor que lo que puedes llevar hoy. No hace falta compararlo con lo que aguanten otras personas.',
            'Hay varias cosas pendientes al mismo tiempo. Podemos dar espacio a esa dificultad sin convertir cada tarea en otra exigencia en el chat.',
        ))
        despues = rng.choice((
            f'El avance en {curso} y la carga que queda pueden existir al mismo tiempo. No necesitas decir que ya está todo bien porque salió una parte.',
            'Una parte hecha no vuelve pequeña la cantidad que aún tienes. Conviene conservar las dos cosas al describir cómo te está yendo.',
            'Lo que cuentas sigue siendo una carga importante para ti. Si necesitas plantearla a un docente o tutor, puedes mostrar qué trabajos coincidieron.',
            f'Gracias por aclarar que no se trata solo de entender {trabajo}. La cantidad total sigue siendo la dificultad que estás señalando.',
        ))
        return primero, respuesta, luego, despues
    if indicador == 'presion_tiempo':
        hora = rng.choice(('las seis', 'las seis y media', 'las siete', 'las siete y media'))
        parte = rng.choice(('la explicación final', 'dos preguntas', 'la parte del procedimiento', 'la revisión del archivo'))
        primero = rng.choice((
            f'El archivo de {curso} cierra a {hora} y siento que no me queda tiempo suficiente para terminar {parte}.',
            f'Me falta {parte} de {trabajo}, pero hay que enviarlo a {hora}. Voy con el tiempo encima para llegar.',
            f'Lo que me apura es la entrega de {curso}: hasta {hora} reciben el archivo y siento que no alcanzo a cerrarlo.',
        ))
        luego = rng.choice((
            f'Sigue pendiente {parte}. El cierre a {hora} no cambió y sigo con la sensación de que no me alcanza el tiempo.',
            f'Avancé en {curso}, pero me queda poco margen para la entrega a {hora}; todavía estoy corriendo con eso.',
            f'Miré la hora otra vez. Todavía me falta cerrar esa parte antes de {hora} y sigo con la prisa de llegar.',
        ))
        respuesta = rng.choice((
            f'La entrega a {hora} te está marcando el ritmo. Podemos mirar una duda concreta de esa parte que falta.',
            f'El plazo de {curso} se siente corto para lo que queda. ¿Qué parte necesitas aclarar ahora?',
            'Estás distinguiendo una dificultad con el tiempo disponible. Podemos trabajar con ese límite real sin exigir que todo salga perfecto.',
            f'Se acerca el cierre y falta {parte}. Una consulta específica puede ayudarnos a no abrir más frentes de los necesarios.',
        ))
        despues = rng.choice((
            f'La hora de cierre a {hora} no cambió. Si necesitas consultar una alternativa con tu docente, puedes explicar lo hecho y lo pendiente.',
            f'La prisa sigue presente en lo de {curso}. ¿Hay una duda de contenido que quieras mirar en concreto?',
            'No hace falta negar la presión solo porque hayas avanzado algo. Si el tiempo no permite completar lo pedido, comunicarlo puede ser una opción.',
            f'Gracias por contar que sigue faltando {parte}. Conviene mantener claro qué puedes hacer en el margen que queda y qué tendrías que consultar.',
        ))
        return primero, respuesta, luego, despues
    if indicador == 'sintomas_fisicos':
        sintoma = rng.choice(('cabeza', 'cuello', 'sueño', 'hombros'))
        relatos = {
            'cabeza': (
                f'Cuando me quedo con lo de {curso}, me empieza un dolor de cabeza que ya he notado otras tardes con los estudios.',
                f'Volví a lo de {curso} y la cabeza me sigue doliendo. Por eso dejé el cuaderno un momento.',
            ),
            'cuello': (
                f'Al trabajar en {trabajo} noto el cuello muy tenso y con dolor; me ha pasado con las tareas estos días.',
                f'Todavía tengo el cuello tenso después de otro rato con lo del colegio, no se me pasó del todo.',
            ),
            'sueño': (
                f'Anoche me quedé pensando en lo de {curso} y me costó dormir. Hoy me siento con cansancio físico por ese mal sueño.',
                f'Sigo con el cuerpo cansado por la noche que pasé pensando en los estudios. Hacer una parte de la tarea no me quitó eso.',
            ),
            'hombros': (
                f'Después de seguir con {trabajo} siento los hombros tensos y me duelen; lo estoy notando al estudiar.',
                f'Los hombros me siguen molestando cuando vuelvo al trabajo del colegio. Es un dolor que sí noto, por eso hago una pausa.',
            ),
        }
        primero, luego = relatos[sintoma]
        respuesta = rng.choice((
            'Gracias por contar la molestia. No puedo confirmar su causa por el chat. Si continúa o se repite, cuéntaselo a una persona adulta y busca orientación de salud.',
            f'Lo que notas al trabajar en {curso} merece cuidado. No necesitas ignorarlo para continuar; avisa a una persona adulta si se mantiene.',
            'Puedes hacer una pausa y decir en casa cómo te sientes. Si el malestar persiste, empeora o es intenso, necesita orientación de salud.',
            f'Has descrito una molestia que vuelve con la actividad escolar. Coméntalo con alguien adulto que pueda acompañarte, sin dar por confirmada una causa solo por el chat.',
        ))
        despues = rng.choice((
            'La molestia sigue presente. No necesitas forzarte a continuar; avisa en casa, y si es intensa, persiste o empeora, busca atención de salud.',
            f'Volvió al retomar {trabajo}. Eso es algo que puedes explicar a una persona adulta; continuar con dolor o agotamiento no tiene por qué ser la única opción.',
            'Que hayas hecho una parte no significa que el cuerpo ya esté bien. Si sigue ocurriendo, busca acompañamiento de una persona adulta y orientación de salud.',
            'Gracias por avisar que continúa. Descansar de la actividad puede ser razonable, pero si persiste o empeora hace falta que te acompañen y revisen esa molestia.',
        ))
        return primero, respuesta, luego, despues
    forma = rng.choice(('expo', 'error', 'concentracion', 'comparacion'))
    relatos = {
        'expo': (
            f'Me dan muchos nervios al pensar que voy a explicar lo de {curso} delante del salón, incluso si entiendo lo que hice.',
            f'Todavía me preocupa quedarme sin palabras cuando explique {trabajo}. La idea vuelve aunque repase lo que sé.',
        ),
        'error': (
            f'En {curso}, cuando una respuesta me sale mal, me quedo con mucha preocupación por si el profe cree que no entendí nada.',
            f'Volví a pensar en una respuesta que di en {curso} y sigo dándole vueltas con preocupación.',
        ),
        'concentracion': (
            f'Con lo de {curso} me preocupo tanto por el resultado que leo el enunciado y me cuesta concentrarme en lo que dice.',
            f'La preocupación por cómo saldrá {trabajo} me volvió a sacar del texto. Leí lo mismo varias veces sin seguirlo.',
        ),
        'comparacion': (
            f'Pienso que todos en el salón harán mejor {trabajo} que yo y me da ansiedad, aunque todavía ni haya visto sus trabajos.',
            f'Sigo comparando mi trabajo de {curso} con lo que imagino que harán los demás, y me mantiene con preocupación.',
        ),
    }
    primero, luego = relatos[forma]
    respuesta = rng.choice((
        f'Lo que ocurre en {curso} te está haciendo sentir mal. Podemos hablar de eso sin usar una nota como medida de tu valor.',
        'Gracias por explicarlo con un caso concreto. Podemos escuchar esa preocupación sin decirte que simplemente dejes de sentirla.',
        f'Entender la actividad y preocuparte por ella pueden ocurrir juntos. ¿Hay un momento de {curso} que se te venga más a la cabeza?',
        'No tienes que restarle importancia para contarlo. Si te está pasando seguido, una persona adulta u orientación del colegio también puede acompañarte.',
    ))
    despues = rng.choice((
        f'La preocupación por {curso} sigue apareciendo. Si se repite o interrumpe tus actividades, busca una persona adulta de confianza u orientación del colegio.',
        'Conversar no obliga a que desaparezca lo que sientes. Si esto continúa pesando, es válido buscar acompañamiento de alguien de confianza.',
        f'Puedes reconocer que hiciste algo de {trabajo} y que esa preocupación continúa. No son relatos que se anulen entre sí.',
        'Gracias por volver a mencionarlo. Si te sigue haciendo sentir mal o te dificulta el día, no necesitas llevarlo sin apoyo de una persona adulta.',
    ))
    return primero, respuesta, luego, despues


def _apoyo_contextual(indicador, contexto, rng):
    trabajo = contexto['tarea']
    curso = contexto['area'].lower()
    if indicador == 'planificacion':
        herramienta = rng.choice(('mi agenda', 'una hoja al lado del cuaderno', 'una nota del celular', 'una tarjeta en el escritorio'))
        primero = rng.choice((
            f'Hoy usé {herramienta} para separar los pasos de {trabajo}. Ya lo tengo por escrito y lo estoy siguiendo.',
            f'Para organizarme con {curso}, anoté en {herramienta} qué partes tenía que hacer y en qué orden.',
            f'Dividí lo de {curso} en pasos y los dejé en {herramienta}. Así estoy llevando esa tarea hoy.',
        ))
        luego = rng.choice((
            f'Volví a {herramienta} y marqué el paso que ya terminé. Dejé escrito qué parte sigue de {trabajo}.',
            f'Ajusté en {herramienta} el orden de dos pasos de {curso}; el primero necesitó más rato del que pensé.',
            f'Miré lo que tenía escrito en {herramienta} y pude retomar justo la parte de {curso} que había dejado.',
        ))
        respuesta = rng.choice((
            f'Estás usando {herramienta} para organizar una actividad concreta. Puede orientarte sin convertirse en una obligación al minuto.',
            'Lo has llevado a una acción: escribir las partes y usarlas para empezar. Esa organización puede seguir siendo flexible.',
            f'En lo de {curso} ya pusiste en práctica una forma de ordenar el trabajo. Puedes conservar solo lo que te resulte útil.',
            f'Has convertido {trabajo} en partes más visibles. La herramienta puede adaptarse si la actividad cambia.',
        ))
        despues = rng.choice((
            f'El cambio en {herramienta} refleja cómo fue realmente la tarea. Puedes seguir ajustándolo cuando haga falta.',
            'Ese registro puede ayudarte a retomar sin reconstruir todo de memoria. No tiene que quedar perfecto para servirte.',
            f'La organización se fue adaptando a {curso}, en lugar de pedirte cumplir un plan que ya no coincidía con lo ocurrido.',
            'Quedó una parte marcada y otra por hacer. Eso permite distinguir el estado de la actividad sin depender solo de recordarlo.',
        ))
        return primero, respuesta, luego, despues
    if indicador == 'automotivacion':
        motivo = rng.choice((
            'aprender cosas que antes no me salían', 'acabar quinto con algo de lo que sentirme bien',
            'conocer mejor qué me gustaría estudiar después', 'ver que mi esfuerzo sí deja algo aprendido',
            'poder explicar una idea con mis propias palabras', 'abrirme opciones cuando termine el colegio',
        ))
        primero = rng.choice((
            f'Con lo de {curso} me doy ánimo recordando que quiero {motivo}. Hoy me lo dije para seguir intentándolo.',
            f'Cuando hago {trabajo}, me recuerdo que me importa {motivo}; eso me ayuda a sostener el intento.',
            f'Hoy me dije que lo de {curso} puede salir por partes y que quiero {motivo}. Así me animé a seguir.',
        ))
        luego = rng.choice((
            f'Volví a decirme que quiero {motivo}. No hace que el trabajo salga solo, pero me dio ánimo para intentar la siguiente parte.',
            f'Me reconocí una parte que sí aprendí en {curso} y me dije que podía continuar sin que todo saliera perfecto.',
            f'Para volver al ejercicio me recordé lo que me importa: {motivo}. Me ayudó a seguir probando.',
        ))
        respuesta = rng.choice((
            f'Para ti, {motivo} es una razón para seguir. Puedes usarla sin exigir sentir entusiasmo todo el tiempo.',
            'Ese motivo es algo que tú estás usando para darte ánimo. No hace falta que todo salga de una vez para reconocer el intento.',
            f'Conectaste la actividad de {curso} con algo que te importa personalmente.',
            f'Te diste ánimo para volver a {trabajo}. Eso no hace desaparecer las dificultades, pero describe una práctica que usaste.',
        ))
        despues = rng.choice((
            'Estás usando una manera propia de sostener el intento. También puedes reconocer tus límites y descansar.',
            f'Volviste a conectar lo de {curso} con tu motivo personal. Puedes reconocer ese esfuerzo sin pedirte hacerlo perfecto.',
            'Esa forma de hablarte te permitió volver a probar. Puedes conservarla sin convertirla en una exigencia de estar bien siempre.',
            f'Lo que cuentas es una acción de ánimo que tú pusiste en práctica. Puede acompañar el aprendizaje de {curso} sin garantizar un resultado concreto.',
        ))
        return primero, respuesta, luego, despues
    persona, pronombre = rng.choice((
        ('mi hermana', 'ella'), ('mi hermano', 'él'), ('mi mamá', 'ella'),
        ('mi papá', 'él'), ('una compañera', 'ella'), ('un compañero', 'él'),
        ('mi profesora', 'ella'), ('mi tutor', 'él'),
    ))
    primero = rng.choice((
        f'Le pedí a {persona} que leyera conmigo la indicación de {trabajo}; me ayudó a entender qué pedían.',
        f'Para aclarar una parte de {curso}, le hice una pregunta a {persona}. Me explicó el paso que no entendía.',
        f'Busqué a {persona} para pedir ayuda con una indicación de {curso}. Lo revisamos y pude entender esa parte.',
    ))
    luego = rng.choice((
        f'Le volví a consultar a {persona} por una frase de la actividad. {pronombre.capitalize()} me mostró qué parte de la consigna tenía que mirar.',
        f'Hablé otra vez con {persona} sobre lo de {curso}; me escuchó y aclaramos una duda concreta del trabajo.',
        f'Le enseñé a {persona} cómo había entendido la indicación después de pedir ayuda, y revisamos esa parte juntos.',
    ))
    respuesta = rng.choice((
        f'Pediste ayuda a {persona} para entender una parte. Puedes elaborar tu propio trabajo a partir de esa aclaración.',
        f'La conversación con {persona} se centró en una duda concreta de {curso}. Pedir una explicación no equivale a que hagan el trabajo por ti.',
        'Buscaste a alguien y recibiste una aclaración específica. Puedes contar qué parte cambió para ti después de entenderla.',
        f'Ya utilizaste un apoyo para {trabajo}. Es una acción tuya, además de la ayuda que recibiste.',
    ))
    despues = rng.choice((
        f'Volviste a consultar a {persona} cuando apareció otra duda. La ayuda puede acompañarte sin reemplazar tu trabajo.',
        f'Pudiste aclarar una parte de {curso} al volver a preguntar. No necesitas esperar a tener todas las dudas juntas para pedir apoyo.',
        'La ayuda quedó en una aclaración concreta. Puedes continuar con tus propias ideas y volver a preguntar si aparece otra duda.',
        f'Tuviste otro intercambio con {persona} sobre la actividad. Gracias por explicar qué apoyo buscaste y qué recibiste.',
    ))
    return primero, respuesta, luego, despues


def _sin_pregunta(texto):
    """Los episodios asincrónicos no dejan preguntas sin respuesta al cambiar tema."""
    if '¿' in texto:
        return texto[:texto.index('¿')].strip() or 'El tiempo disponible es una parte concreta de lo que estás contando. Podemos tenerlo presente al mirar lo que falta.'
    return texto


def _registro(texto, voz):
    # Cambios moderados de registro; se aplican también a las citas antes de
    # validarlas. No borran negaciones ni cambian hechos, frecuencias o unidades.
    cambios = {
        'coloquial': {'colegio': 'cole', 'exposición': 'expo', 'profesora': 'profe', 'profesor': 'profe', 'porque': 'pq'},
        'breve': {'Por ejemplo, ': 'Por ejemplo: ', 'Todavía': 'Aún', 'todavía': 'aún'},
        'detallista': {}, 'serena': {},
    }
    for original, reemplazo in cambios.get(voz, {}).items():
        texto = re.sub(r'\b' + re.escape(original) + r'\b', reemplazo, texto)
    return texto


def _evidencia(indicador, cita, senal):
    etiquetas = {
        'dificultad': 'El estudiante relata una dificultad',
        'recurso': 'El estudiante relata una práctica de afrontamiento que utiliza',
        'ausencia_explicita': 'El estudiante niega explícitamente una dificultad',
    }
    return {
        'indicador': indicador, 'cita': cita, 'senal': senal,
        'observacion': f'{etiquetas[senal]}: «{cita}».',
    }


def _envolver(texto, voz, rng, variante):
    """Cambia el registro sin corregir ni modificar las citas de evidencia."""
    if variante % 4:
        return texto
    if voz == 'breve':
        prefijos = ('Ah, otra cosa. ', 'Eso sí. ', 'Te cuento. ', '')
    elif voz == 'coloquial':
        prefijos = ('Oye. ', 'Ah, otra cosa. ', 'Bueno. ', '')
    elif voz == 'detallista':
        prefijos = ('Te explico. ', 'Hay un detalle más. ', 'Te cuento un poco. ', '')
    else:
        prefijos = ('También quería contarte esto. ', 'Pensé en otro detalle. ', '', '')
    return rng.choice(prefijos) + texto


def validar_dialogo(pares, dificultades, recursos):
    """Revisa autoría de citas, cobertura de perfiles y límites de los textos."""
    if not 25 <= len(pares) <= 29:
        raise ValueError('La conversación debe tener entre 25 y 29 pares.')
    conteo = Counter()
    textos = set()
    bloques = []
    for par in pares:
        bloques.append(par['bloque'])
        for rol in ('usuario', 'asistente'):
            texto = par[rol]
            if not isinstance(texto, str) or not 1 <= len(texto) <= 2000:
                raise ValueError('Hay un mensaje vacío o demasiado largo.')
        if par['usuario'] in textos:
            raise ValueError('Un estudiante repite exactamente el mismo mensaje.')
        textos.add(par['usuario'])
        for evidencia in par['evidencias']:
            indicador, senal, cita = (evidencia[k] for k in ('indicador', 'senal', 'cita'))
            if indicador not in DIFICULTADES + RECURSOS:
                raise ValueError('Indicador no reconocido.')
            if not 1 <= len(cita) <= 400 or cita not in par['usuario']:
                raise ValueError('La cita debe ser un fragmento literal del alumno.')
            if indicador in DIFICULTADES and senal == 'recurso':
                raise ValueError('Una dificultad no puede anotarse como recurso.')
            conteo[indicador, senal] += 1
    if bloques != sorted(bloques) or set(bloques) != set(range(5)):
        raise ValueError('Los cinco bloques deben aparecer en orden.')
    reales = {i for (i, s), n in conteo.items() if s == 'dificultad' and n}
    if reales != set(dificultades):
        raise ValueError('La cobertura de dificultades no coincide con el perfil.')
    for indicador in dificultades:
        if conteo[indicador, 'dificultad'] < 2:
            raise ValueError('Cada dificultad necesita dos relatos concordantes.')
    for indicador in recursos:
        if conteo[indicador, 'recurso'] < 2:
            raise ValueError('Cada recurso necesita dos prácticas relatadas.')
    return {
        'pares': len(pares), 'mensajes': 2 * len(pares),
        'dificultades': sorted(reales),
        'evidencias': sum(conteo.values()),
    }


def construir_dialogo(indice, perfil, rng):
    """Construye una tarde de 25–29 intercambios para un perfil de quinto.

    Las frecuencias de algunos relatos son expresiones explícitas redactadas en
    el mensaje, no valores ocultos para rellenar el Excel. Las conversaciones
    sin ellas conservan la falta de información en el exportador del sistema.
    """
    dificultades = list(perfil.get('dificultades', []))
    recursos = list(perfil.get('recursos', []))
    if set(dificultades) - set(DIFICULTADES) or set(recursos) - set(RECURSOS):
        raise ValueError('El perfil contiene códigos de indicadores desconocidos.')
    if len(set(dificultades)) != len(dificultades) or len(set(recursos)) != len(recursos):
        raise ValueError('El perfil repite un indicador.')
    nombre = perfil.get('nombre', '').split()[0]
    if not nombre:
        raise ValueError('Falta el nombre del perfil.')
    voz = perfil.get('voz', VOCES[indice % len(VOCES)])
    contextos = CONTEXTOS + tuple(CONTEXTOS_EXTRA)
    contexto = contextos[perfil.get('contexto_idx', indice) % len(contextos)]
    if indice % 4 == 0:
        contexto = _contexto_numerico(indice // 4, rng)
    pasatiempo = PASATIEMPOS[(indice * 5 + rng.randrange(len(PASATIEMPOS))) % len(PASATIEMPOS)]
    pares = []

    def agregar(usuario, asistente, bloque, evidencias=(), estilo=False):
        if estilo:
            usuario = _envolver(usuario, voz, rng, len(pares) + indice)
        usuario = _registro(usuario, voz)
        evidencias = [dict(e) for e in evidencias]
        for evidencia in evidencias:
            evidencia['cita'] = _registro(evidencia['cita'], voz)
            evidencia['observacion'] = _registro(evidencia['observacion'], voz)
        pares.append({'usuario': usuario, 'asistente': asistente, 'evidencias': evidencias, 'bloque': bloque})

    saludos = {
        'breve': ('Hola, ya salí del cole.', 'Buenas, estoy por acá un rato.', 'Hola. Soy de quinto, acabo de llegar.', 'Holaa, ¿puedo conversar un rato?'),
        'coloquial': ('Holaa, recién llego del cole jaja.', 'Buenas, ya estoy en casa. Qué tal.', 'Holaa, soy de 5to. Me dijeron que podía hablar por acá.', 'Hey, ya salí del colegio y vine un rato al chat.'),
        'detallista': ('Hola, estoy en quinto de secundaria. Llegué hace un rato del colegio y quería conversar.', 'Buenas tardes. Ya llegué a casa y tengo el cuaderno por aquí.', 'Hola, quería probar conversar mientras hago algunas cosas de la tarde.', 'Hola. Hoy salimos del colegio y me quedó un rato para entrar al chat.'),
        'serena': ('Hola, ya estoy de vuelta del colegio.', 'Buenas, quería conversar un rato esta tarde.', 'Hola, soy de quinto. Estoy en casa ahora.', 'Hola, por aquí ya pasó la salida del colegio.'),
    }
    agregar(rng.choice(saludos[voz]), rng.choice((
        f'Hola, {nombre}. Puedes conversar a tu ritmo. ¿Qué tienes por ahí esta tarde?',
        f'Hola, {nombre}. Te leo. Puedes empezar por lo que te apetezca contar.',
        f'Hola, {nombre}. ¿Vienes con algo del colegio o prefieres empezar por otro tema?',
    )), 0)
    agregar(rng.choice((
        f'Tengo por aquí {contexto["tarea"]} de {contexto["area"]}.',
        f'Ando viendo lo de {contexto["area"]}: nos dejaron {contexto["tarea"]}.',
        f'En mi cuaderno tengo {contexto["tarea"]}. Es para {contexto["area"]}.',
        f'Para empezar te cuento de {contexto["tarea"]}. Lo estamos haciendo en {contexto["area"]}.',
        f'Ahorita tengo abierta la actividad de {contexto["area"]}, {contexto["tarea"]}.',
    )), rng.choice((
        f'Cuéntame qué parte están trabajando en {contexto["area"]}.',
        f'¿Qué indica esa actividad de {contexto["area"]}?',
        f'Te leo. ¿De qué trata {contexto["tarea"]}?',
        'Puedes contarme el enunciado o la parte que estás mirando.',
    )), 0)
    agregar(contexto['detalle'], contexto['detalle_bot'], 0, estilo=True)
    hobby_temprano = indice % 3 != 0
    if hobby_temprano:
        agregar(f'Y fuera del cole me gusta {pasatiempo[0]}. {pasatiempo[1]}', pasatiempo[2], 0)
        agregar(pasatiempo[3], pasatiempo[4], 0, estilo=True)
    else:
        agregar(contexto['curiosidad'], contexto['curiosidad_bot'], 0, estilo=True)

    agregar(contexto['pregunta'], contexto['respuesta'], 1, estilo=True)
    agregar(contexto['segunda'], contexto['respuesta_segunda'], 1, estilo=True)

    rng.shuffle(dificultades)
    rng.shuffle(recursos)
    continuaciones = []
    episodios = [('dificultad', indicador) for indicador in dificultades]
    episodios.extend(('recurso', indicador) for indicador in recursos)
    # El orden cambia sin romper el orden interno de cada episodio.
    rng.shuffle(episodios)
    for orden, (senal, indicador) in enumerate(episodios):
        banco = EPISODIOS if senal == 'dificultad' else APOYOS
        if rng.random() < 0.78:
            episodio = (_episodio_contextual if senal == 'dificultad' else _apoyo_contextual)(indicador, contexto, rng)
        else:
            episodio = banco[indicador][(indice + orden * 3 + rng.randrange(len(banco[indicador]))) % len(banco[indicador])]
        primero, respuesta, luego, respuesta_luego = episodio
        # Construcciones en primera persona sin asumir género por el nombre.
        for anterior, siguiente in (
            ('me siento sobrepasado por la cantidad', 'la cantidad me sobrepasa'),
            ('me hace ir apurado', 'me hace ir con prisa'),
            ('Me pongo muy nervioso', 'Me dan muchos nervios'),
            ('me mantiene preocupado', 'me mantiene con preocupación'),
        ):
            primero = primero.replace(anterior, siguiente)
            luego = luego.replace(anterior, siguiente)
        evidencias = [_evidencia(indicador, primero, senal)]
        # Una parte de los perfiles expresa frecuencia y periodo; el resto no
        # recibe frecuencias inventadas desde fuera de lo que dice el alumno.
        if (indice + orden) % 5 == 0:
            frecuencia = ('algunas veces', 'casi siempre', 'rara vez')[(indice + orden) % 3]
            acciones = {
                'sobrecarga_academica': 'tengo demasiadas tareas del colegio para lo que puedo llevar',
                'presion_tiempo': 'me falta tiempo para las entregas del colegio',
                'sintomas_psicologicos': 'me preocupo por mis estudios y le doy vueltas a eso',
                'planificacion': 'organizo mis tareas del colegio y uso una lista para llevarlas',
                'automotivacion': 'me animo para continuar con mis estudios',
                'busqueda_soporte': 'pido ayuda para entender alguna parte de las tareas',
            }
            if indicador == 'sintomas_fisicos' and 'cabeza' in primero:
                acciones[indicador] = 'me duele la cabeza por los estudios'
            if indicador in acciones:
                cita_frecuencia = f'Esta semana {frecuencia} {acciones[indicador]}.'
                entrada = cita_frecuencia + ' ' + primero
                evidencias.insert(0, _evidencia(indicador, cita_frecuencia, senal))
            else:
                entrada = primero
        else:
            entrada = primero
        agregar(entrada, _sin_pregunta(respuesta), 1, evidencias, estilo=True)
        continuaciones.append((indicador, senal, luego, _sin_pregunta(respuesta_luego)))

    if not dificultades:
        sin_dificultad = (
            ('Por el colegio hoy no siento dolor ni cansancio físico.', 'sintomas_fisicos'),
            ('Hoy estoy sin nervios ni preocupación por mis estudios.', 'sintomas_psicologicos'),
            ('La cantidad de tareas que tengo ahora no me está sobrepasando.', 'sobrecarga_academica'),
            ('Hoy sí tengo tiempo suficiente para las entregas del colegio, no estoy a las carreras.', 'presion_tiempo'),
        )
        primeras = sin_dificultad[:2]
        texto = primeras[0][0] + ' Por ese lado estoy bien hoy.'
        agregar(texto, 'Gracias por contar cómo estás hoy. Podemos seguir con lo del cuaderno o conversar de otra cosa que te interese.',
                1, [_evidencia(primeras[0][1], primeras[0][0], 'ausencia_explicita')], estilo=True)

    comidas = (
        'Voy a almorzar y vuelvo por acá después.',
        'Me llaman para comer, dejo el cuaderno un rato. Luego vuelvo.',
        'Ya está el almuerzo. Voy a hacer una pausa y regreso.',
        'Voy a comer algo antes de seguir. Te escribo al volver.',
        'Dejo la actividad aquí un rato, ya sirvieron la comida.',
        'Ya escuché que me llaman para almorzar. Ahorita dejo el chat y vuelvo después.',
        'Me voy un momento a la mesa, luego retomo el cuaderno.',
        'Hago una pausa para comer, ya está el plato esperándome.',
        'Primero voy a almorzar. Después regreso a esta misma conversa.',
        'Ya toca comer por acá. Guardo el celular un rato.',
        'Voy a dejar esto abierto mientras almuerzo. Luego sigo.',
        'Por aquí ya están almorzando. Me uno y regreso al rato.',
    )
    agregar(rng.choice(comidas), rng.choice((
        'De acuerdo, que disfrutes el almuerzo. Puedes volver cuando quieras.',
        'Está bien. Dejamos la conversación aquí y la retomas a tu ritmo.',
        'Claro, haz tu pausa. Aquí puedes continuar después.',
        'Que disfrutes la comida. No hace falta responder durante la pausa.',
        'Te leo cuando regreses. Puedes dejar la actividad en este punto.',
        'Está bien cerrar un rato el cuaderno y comer. La conversación queda aquí.',
        'Hasta el regreso. Puedes continuar desde esta misma conversación.',
        'Claro. Cuando vuelvas, seguimos con lo que te interese contar.',
    )), 1)

    agregar(rng.choice((
        'Ya volví. Dejé todo como estaba, sigo con el mismo cuaderno.',
        'Regresé, ya almorcé. Retomo lo que teníamos por acá.',
        'Acá estoy otra vez. Ya pasó el almuerzo.',
        'Volví al chat. Tengo abierta la misma actividad de antes.',
        'Listo, volví después de comer. ¿Seguimos con lo de antes?',
        'Ya estoy de nuevo por acá, con el cuaderno en el mismo sitio.',
        'Regresé al chat. Terminé de almorzar y dejé la mesa libre.',
        'Acá otra vez. Ya pasó mi pausa para comer.',
    )), rng.choice((
        f'Ya estás de vuelta. Habíamos hablado de {contexto["tarea"]}; podemos continuar desde ahí.',
        f'Sí, podemos seguir. Lo último del cuaderno era {contexto["tarea"]}.',
        f'Te leo de nuevo. Si quieres, retomamos esa actividad de {contexto["area"]}.',
        f'Claro. Puedes contar qué pasó con {contexto["tarea"]} o traer otro tema.',
    )), 2)
    agregar(contexto['practica'], contexto['practica_bot'], 2, estilo=True)
    agregar(contexto['avance'], contexto['avance_bot'], 2, estilo=True)
    if hobby_temprano:
        agregar(contexto['curiosidad'], contexto['curiosidad_bot'], 2, estilo=True)
    else:
        agregar(f'Y fuera del cole me gusta {pasatiempo[0]}. {pasatiempo[1]}', pasatiempo[2], 2)
        agregar(pasatiempo[3], pasatiempo[4], 2, estilo=True)

    rng.shuffle(continuaciones)
    for indicador, senal, texto, respuesta in continuaciones:
        agregar(texto, respuesta, 3, [_evidencia(indicador, texto, senal)], estilo=True)

    if not dificultades:
        texto, indicador = sin_dificultad[2 + indice % 2]
        agregar(texto, 'Puedes contar también cuando un día va sin grandes dificultades. No hace falta buscar un problema para poder conversar.',
                3, [_evidencia(indicador, texto, 'ausencia_explicita')], estilo=True)

    # Completar historias de baja carga con contenido cotidiano y académico,
    # sin introducir síntomas ni prácticas de afrontamiento que no se eligieron.
    objetivo = 25 + ((indice * 7 + len(recursos)) % 5)
    # Quedan tres pares de cierre; la respuesta sobre el hobby ya siguió a su
    # pregunta, sin interponer otro tema ni dejarla esperando durante una hora.
    faltan = max(0, objetivo - (len(pares) + 3))
    disponibles = list(RELLENO)
    rng.shuffle(disponibles)
    for usuario, asistente in disponibles[:faltan]:
        # Mantener respuestas cerradas evita preguntas que el turno siguiente
        # ignore; las preguntas de estos detalles se contestan en el mismo par.
        if asistente.endswith('?'):
            respuestas = {
                'participar o prefieres escuchar?': ' Yo prefiero escuchar cómo lo hacen y después leer mi parte normal.',
                'formal o más parecido a cómo son en el salón?': ' Creo que queremos algo más parecido a cómo somos todos los días.',
                '¿Qué habías dibujado?': ' Había dibujado un paisaje con árboles y una banca.',
            }
            for final, respuesta in respuestas.items():
                if asistente.endswith(final):
                    usuario += respuesta
                    asistente = asistente[:asistente.rfind('¿')].strip() or 'Gracias por ese detalle.'
                    break
        agregar(usuario, asistente, 3, estilo=True)

    detalles_finales = (
        ('Ya la luz del cuarto se ve distinta. Se me pasó la tarde entre una cosa y otra.', 'La tarde fue pasando con varias pausas y temas. Puedes dejar aquí la conversación cuando lo necesites.'),
        ('Me quedé con una hoja medio llena de ejemplos de la actividad y otra con dibujos.', 'Es un registro bastante tuyo de esta tarde: hubo trabajo y también otros momentos.'),
        ('El chat quedó larguito jaja, empezamos por una tarea y terminamos hablando de varias cosas.', 'Sí, la conversación tuvo espacio para la actividad y para lo que fuiste contando entre medias.'),
        ('Ya guardé el cuaderno que tenía abierto. Dejo esa parte de la tarde hasta acá.', 'Puedes cerrar esta parte y retomar lo que necesites en otro momento.'),
        (f'Dejé una marca en la hoja de {contexto["area"]} para reconocer lo que hice hoy. Ya voy guardando mis cosas.', 'Puedes dejar registrada esta parte y cerrar por hoy. No hace falta añadir otra actividad para terminar la conversación.'),
        (f'Lo que empezó con {contexto["tarea"]} terminó siendo una conversa de toda la tarde.', 'Hubo espacio para esa actividad y para otros temas que fuiste trayendo. Puedes cerrar a tu ritmo.'),
        (f'Por acá ya estoy recogiendo las hojas de {contexto["area"]}. Estuvieron dando vueltas en la mesa toda la tarde.', 'Puedes dejar este punto como el cierre de hoy y retomar más adelante lo que necesites.'),
        (f'Entre {contexto["area"]} y lo de {pasatiempo[0]}, hoy conté un poco de todo jaja.', 'Fuiste trayendo partes distintas de tu día. Gracias por compartirlas.'),
        ('Ya está oscureciendo distinto por la ventana. Me acabo de dar cuenta de todo lo que avanzó la tarde.', 'A veces se nota el paso de la tarde por esos detalles. Puedes cerrar aquí sin tener que traer otro tema.'),
        ('Ya bajé el brillo de la pantalla. Por hoy me quedo con lo que hablamos hasta acá.', 'De acuerdo. Puedes dejar la conversación en este punto.'),
    )
    texto, respuesta = rng.choice(detalles_finales)
    agregar(texto, respuesta, 4, estilo=True)
    if dificultades:
        cierres = (
            ('No diría que ya quedó todo resuelto, pero pude explicarte lo que estaba pasando con el colegio.', 'Gracias por ponerlo en palabras. No necesitas cerrar la conversación diciendo que todo está resuelto. Puedes volver y buscar acompañamiento de alguien de confianza si lo necesitas.'),
            ('Algunas cosas siguen igual. Por lo menos pude hablarlo sin estar contestando como en un examen.', 'Está bien que haya cosas pendientes. Lo que contaste no tiene que convertirse en una respuesta perfecta ni en una conclusión rápida.'),
            ('Hoy pude hacer una parte del trabajo. Lo demás que te conté sigue ahí, lo voy viendo.', 'Puedes reconocer esa parte hecha y mantener presente lo que todavía necesita atención. Si lo que sientes continúa pesando, busca acompañamiento de una persona adulta de confianza.'),
            ('Ya voy cerrando por hoy. Me sirvió conversar, aunque no se arregla toda la tarde solo por hablar.', 'Sí, conversar puede ser un espacio sin prometer que cambie todo. Puedes retomar cuando quieras y apoyarte también en personas de confianza.'),
        )
    else:
        cierres = (
            ('Estuvo buena la conversa. No venía con un problema, solo con ganas de hablar mientras hacía mis cosas.', 'También hay espacio para eso. Gracias por compartir parte de tu tarde.'),
            ('Hoy fue un día bastante normal para mí, pero igual estuvo bien pasar por acá.', 'Los días cotidianos también tienen cosas para contar. Puedes volver cuando te apetezca conversar.'),
            ('No tengo nada más en particular. Ya salió la actividad que tenía abierta y hablamos bastante.', 'Puedes dejar la conversación aquí. Gracias por compartir lo del colegio y tus otros intereses.'),
            ('Me voy quedando sin tema jaja. Por hoy estuvo bien, hice mi actividad y conversé un rato.', 'Está bien cerrar cuando ya no tengas más que contar. No hace falta buscar otro tema por obligación.'),
        )
    texto, respuesta = rng.choice(cierres)
    agregar(texto, respuesta, 4, estilo=True)
    despedidas = (
        ('Ya me voy, gracias. Nos vemos.', 'Hasta luego. Que tengas una buena tarde.'),
        ('Bueno, cierro por acá. Chauu.', 'Chau. Puedes volver cuando quieras conversar.'),
        ('Listo, gracias por la conversa. Hasta otra.', 'Gracias a ti por compartir. Hasta otra.'),
        ('Ahora sí, me desconecto. Cuídate.', 'Hasta luego, y cuídate también.'),
    )
    texto, respuesta = rng.choice(despedidas)
    agregar(texto, respuesta, 4)
    validar_dialogo(pares, dificultades, recursos)
    return pares


def auditar_variedad(dialogos):
    """Métricas de revisión del corpus; no certifican realismo ni salud mental."""
    estudiantes = [par['usuario'] for dialogo in dialogos for par in dialogo]
    asistentes = [par['asistente'] for dialogo in dialogos for par in dialogo]
    bloques = Counter(par['bloque'] for dialogo in dialogos for par in dialogo)
    return {
        'conversaciones': len(dialogos),
        'mensajes': 2 * len(estudiantes),
        'textos_estudiante_distintos': len(set(estudiantes)),
        'textos_asistente_distintos': len(set(asistentes)),
        'pares_minimos': min(map(len, dialogos), default=0),
        'pares_maximos': max(map(len, dialogos), default=0),
        'bloques': dict(sorted(bloques.items())),
        'citas_no_literales': sum(
            e['cita'] not in par['usuario']
            for dialogo in dialogos for par in dialogo for e in par['evidencias']
        ),
        'referencias_semanas_programa': sum(
            bool(re.search(r'\bsemana\s+[1-4]\b', texto, re.I))
            for texto in estudiantes + asistentes
        ),
    }
