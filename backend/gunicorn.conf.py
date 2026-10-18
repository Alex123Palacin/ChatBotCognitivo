# Un proceso conserva el límite de login en memoria y evita multiplicar
# escritores sobre SQLite. Los hilos permiten atender consultas durante el chat.
bind = '0.0.0.0:8000'
workers = 1
worker_class = 'gthread'
threads = 4
timeout = 210
graceful_timeout = 210
accesslog = '-'
errorlog = '-'
capture_output = True
# Django interpreta el protocolo enviado por nuestro proxy privado.
forwarded_allow_ips = ''
