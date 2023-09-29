[supervisord]
logfile_maxbytes=1MB
logfile_backups=2
nodaemon=true

[eventlistener:dependent-startup]
command=python3 -m supervisord_dependent_startup
autostart=true
autorestart=unexpected
startretries=0
exitcodes=0,3
events=PROCESS_STATE
buffer_size=1024

[program:rsyslogd]
command=/usr/sbin/rsyslogd -n -iNONE
priority=1
autostart=false
autorestart=false
stdout_logfile=syslog
stderr_logfile=syslog
dependent_startup=true

[program:wait-interfaces]
command=/usr/bin/wait-interfaces.sh
priority=2
startsecs=0
autostart=false
autorestart=false
dependent_startup=true

[program:syncd]
command=/usr/bin/syncd -s -p /etc/sai.d/sai.profile
priority=5
autostart=false
autorestart=true
stdout_logfile=syslog
stderr_logfile=syslog
dependent_startup=true
dependent_startup_wait_for=rsyslogd:running wait-interfaces:exited

