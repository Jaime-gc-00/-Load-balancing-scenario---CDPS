Script que genera un escenario completo de balanceo de carga.

Comandos disponibles:

python3 auto-p2.py <orden> <parametros>

Órdenes:

- prepare : prepara el escenario, admite un segundo parámetro para indicar el número de servidores que se desea crear (entre 1 y 5). 
- launch : arranca el escenario, admite un segundo parámetro para arrancar máquinas individualmente. 
- stop : para el escenario, admite un segundo parámetro para parar máquinas individualmente. 
- release: borra todo el escenario y la carpeta temporal creada.
- monitor: abre diferentes consolas con el estado de cada máquina.
- balance: con el balanceador (LB) parado, se permite dar distintos pesos a cada servidor. Introducir tantos paramétros como nº se servidores. 