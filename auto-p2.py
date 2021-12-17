#! /usr/bin/python

#INTEGRANTES: Jaime Guerrero Carrasco, Jorge Molina Lafuente y Juan Gonzalez Jimenez

from subprocess import call
import sys
import subprocess
import json
import os

#la orden a ejecutar sera el primer parametro
orden = str(sys.argv[1])

#En el XML de las maquinas virtuales hay que poner el path completo de los ficheros de imagenes
#path completo
cwd = str(os.getcwd())




def prepare():

    #CREACION DE DIRECTORIOS TEMPORALES
    #creamos un directorio temporal /mnt/tmp/auto-p2 donde guardaremos los archivos generados por el script.
    call(["mkdir /mnt/tmp/auto-p2"],shell=True)

    #comprobamos si se ha introducido un segundo parametro en la orden 
    #dudamos entre poner ==3 o >=3 ya que con ==3 si pones mas de 2 parametros se iria al caso por defecto
    #y con >=3 ignoraria los posteriores a sys.argv[2] y solo usaria este
    #de cualquier forma que la longitud sea mayor de 3 no es muy probable
    if len(sys.argv) == 3:  
        #comprobamos si el numero de servidores a crear esta entre 1 y 5
        if int(sys.argv[2])>=1 and int(sys.argv[2])<=5:
            x=str(sys.argv[2])
        else:
            #Escribe un error si no es un numero entre 1 y 5
            print("ERROR. El numero de servidores posibles a crear esta entre 1 y 5")
            sys.exit()
    else:
        #por defecto el numero de servidores sera 3
        x="3"    

    #CREAMOS EL ARCHIVO JSON
    num_servers = {
        "num_serv" : x
    }
    with open('/mnt/tmp/auto-p2/auto-p2.json', 'w') as file:
        json.dump(num_servers, file) #si num_servers tuviera x datos habria que incluir indent=x

    #DENTRO DE prepare() PODEMOS USAR ESTA VARIABLE PARA REFERIRNOS AL NUMERO DE SERVIDORES
    numero_de_servidores = int(x)

    #DEBEMOS CREAR UN NUEVO DIRECTORIO PARA PODER HACER COPIAS DE hosts Y haproxy CON PERMISOS PARA MODIFICARLOS
    call(["mkdir /mnt/tmp/auto-p2/dir_for_permissions"],shell=True)

#################     C1      #######################

    #creamos la imagen y el xml para c1 dentro de la carpeta temporal utilizando las plantillas 
    call(["qemu-img create -f qcow2 -b "+ cwd +"/cdps-vm-base-pc1.qcow2 /mnt/tmp/auto-p2/c1.qcow2"], shell=True)
    call(["cp "+ cwd +"/plantilla-vm-pc1.xml /mnt/tmp/auto-p2/c1.xml"], shell=True)
    
    #CREACION DE C1.XML
    #creamos las variables correspondientes a c1.xml y a la plantilla xml
    f1=open(cwd +"/plantilla-vm-pc1.xml",'r')
    f2=open("/mnt/tmp/auto-p2/c1.xml",'w')

    #Recorremos cada linea de la plantilla y en las lineas donde haya XXX sustituimos por el valor adecuado
    for line in f1:
        if "<name>XXX</name>" in line:
            f2.write(line.replace("XXX","C1"))
        elif "/mnt/tmp/XXX/XXX.qcow2" in line:
            f2.write(line.replace("/mnt/tmp/XXX/XXX", "/mnt/tmp/auto-p2/c1"))
        elif "<source bridge=\"XXX\"/>" in line:  #hace falta escapar las comillas
            f2.write(line.replace("XXX", "LAN1"))
        else:
	        f2.write(line)
    f2.close()  
    f1.close()

    #creamos el archivo de hostname de c1 y ademas escribimos dentro de el "c1"
    call(["echo c1 > /mnt/tmp/auto-p2/c1_hostname"], shell=True)
    #ahora creamos el archivo interfaces de c1 y escribimos su contenido
    f=open("/mnt/tmp/auto-p2/c1_interfaces",'w')
    f.write("auto lo\n")
    f.write("iface lo inet loopback\n")
    f.write("auto eth0\n")
    f.write("iface eth0 inet static\n")
    f.write("\taddress 10.0.1.2\n")
    f.write("\tnetmask 255.255.255.0\n")
    f.write("\tgateway 10.0.1.1\n")
    f.write("\tdns-nameservers 10.0.1.1")
    f.close()

    #Vamos a realizar la configuracion de red de c1 de forma permanente.
    #Copia de los archivos de configuracion de c1 del directorio temporal del host a la maquina virtual.
    #INTERFACES
    call(["cp /mnt/tmp/auto-p2/c1_interfaces /mnt/tmp/auto-p2/interfaces"], shell=True)
    call(["sudo virt-copy-in -a /mnt/tmp/auto-p2/c1.qcow2 /mnt/tmp/auto-p2/interfaces /etc/network"], shell=True)
    #HOSTNAME
    call(["cp /mnt/tmp/auto-p2/c1_hostname /mnt/tmp/auto-p2/hostname"], shell=True)
    call(["sudo virt-copy-in -a /mnt/tmp/auto-p2/c1.qcow2 /mnt/tmp/auto-p2/hostname /etc"], shell=True)

    #PARA MODIFICAR EL ARCHIVOS HOSTS PRIMERO DEBEMOS EXTRAERLO DE LA MAQUINA VIRTUAL
    call(["sudo virt-copy-out -a /mnt/tmp/auto-p2/c1.qcow2 /etc/hosts /mnt/tmp/auto-p2"], shell=True)
    #AHORA LO PODEMOS EDITAR
    original_hosts=open("/mnt/tmp/auto-p2/hosts",'r')
    nuevo_hosts=open("/mnt/tmp/auto-p2/dir_for_permissions/hosts",'w')
    for line in original_hosts:
        if "127.0.1.1" in line:
            nuevo_hosts.write("127.0.1.1 c1\n")
        else:
            nuevo_hosts.write(line)
    original_hosts.close()
    nuevo_hosts.close()

    #VOLVEMOS A INTRODUCIR EL HOSTS UNA VEZ MODIFICADO EN /etc DE lb.qcow2
    call(["sudo virt-copy-in -a /mnt/tmp/auto-p2/c1.qcow2 /mnt/tmp/auto-p2/dir_for_permissions/hosts /etc"], shell=True)

#################     FINAL C1      #######################

#################     LB      #######################

    #creamos la imagen y el xml para lb dentro de la carpeta temporal utilizando las plantillas 
    call(["qemu-img create -f qcow2 -b "+ cwd +"/cdps-vm-base-pc1.qcow2 /mnt/tmp/auto-p2/lb.qcow2"], shell=True)
    call(["cp "+ cwd +"/plantilla-vm-pc1.xml /mnt/tmp/auto-p2/lb.xml"], shell=True)

    #CREACION DE LB.XML
    #creamos las variables correspondientes a lb.xml y a la plantilla xml
    f1=open(cwd +"/plantilla-vm-pc1.xml",'r')
    f2=open("/mnt/tmp/auto-p2/lb.xml",'w')

    #Recorremos cada linea de la plantilla y en las lineas donde haya XXX sustituimos por el valor adecuado
    #Ademas creamos una nueva interfaz para la LAN2
    for line in f1:
        if "<name>XXX</name>" in line:
            f2.write(line.replace("XXX","LB"))
        elif "/mnt/tmp/XXX/XXX.qcow2" in line:
            f2.write(line.replace("/mnt/tmp/XXX/XXX", "/mnt/tmp/auto-p2/lb"))
        elif "<source bridge=\"XXX\"/>" in line:  #hace falta escapar las comillas
            f2.write(line.replace("XXX", "LAN1"))
        #EN LB HAY QUE INCLUIR OTRA INTERFAZ PARA LAN2
        elif "</interface>" in line:
            f2.write("\t</interface>\n")
            f2.write("\t<interface type='bridge'>\n")
            f2.write("\t\t<source bridge='LAN2'/>\n")
            f2.write("\t\t<model type='virtio'/>\n")
            f2.write("\t</interface>\n")
        else:
	        f2.write(line)
    f2.close()  
    f1.close()

    #creamos el archivo de hostname de lb y ademas escribimos dentro de el "lb"
    call(["echo lb > /mnt/tmp/auto-p2/lb_hostname"], shell=True)
    #ahora creamos el archivo interfaces de lb y escribimos su contenido
    f=open("/mnt/tmp/auto-p2/lb_interfaces",'w')
    f.write("auto lo\n")
    f.write("iface lo inet loopback\n")
    f.write("auto eth0\n")
    f.write("iface eth0 inet static\n")
    f.write("\taddress 10.0.1.1\n")
    f.write("\tnetmask 255.255.255.0\n")
    f.write("auto eth1\n")
    f.write("iface eth1 inet static\n")
    f.write("\taddress 10.0.2.1\n")
    f.write("\tnetmask 255.255.255.0")
    f.close()

    #Vamos a realizar la configuracion de red de lb de forma permanente.
    #Copia de los archivos de configuracion de lb del directorio temporal del host a la maquina virtual.
    #INTERFACES
    call(["cp /mnt/tmp/auto-p2/lb_interfaces /mnt/tmp/auto-p2/interfaces"], shell=True)
    call(["sudo virt-copy-in -a /mnt/tmp/auto-p2/lb.qcow2 /mnt/tmp/auto-p2/interfaces /etc/network"], shell=True)
    #HOSTNAME
    call(["cp /mnt/tmp/auto-p2/lb_hostname /mnt/tmp/auto-p2/hostname"], shell=True)
    call(["sudo virt-copy-in -a /mnt/tmp/auto-p2/lb.qcow2 /mnt/tmp/auto-p2/hostname /etc"], shell=True)

    #PARA MODIFICAR EL ARCHIVOS HOSTS PRIMERO DEBEMOS EXTRAERLO DE LA MAQUINA VIRTUAL 
    call(["sudo virt-copy-out -a /mnt/tmp/auto-p2/lb.qcow2 /etc/hosts /mnt/tmp/auto-p2"], shell=True)
    #AHORA LO PODEMOS EDITAR 
    original_hosts=open("/mnt/tmp/auto-p2/hosts",'r')
    nuevo_hosts=open("/mnt/tmp/auto-p2/dir_for_permissions/hosts",'w')
    for line in original_hosts:
        if "127.0.1.1" in line:
            nuevo_hosts.write("127.0.1.1 lb\n")
        else:
            nuevo_hosts.write(line)
    original_hosts.close()
    nuevo_hosts.close()

    #VOLVEMOS A INTRODUCIR EL HOSTS UNA VEZ MODIFICADO EN /etc DE lb.qcow2
    call(["sudo virt-copy-in -a /mnt/tmp/auto-p2/lb.qcow2 /mnt/tmp/auto-p2/dir_for_permissions/hosts /etc"], shell=True)  

    #Para que el balanceador de trafico funcione como router al arrancar editamos el fichero /etc/sysctl.conf de lb.qcow2
    call(["sudo virt-edit -a /mnt/tmp/auto-p2/lb.qcow2 /etc/sysctl.conf -e 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/'"],shell=True)

    ## MEJORA HAPROXY ##
    #Para que el HAproxy pueda ejecutarse, es necesario parar el servidor apache2 
    #call(["sudo service apache2 stop"], shell=True)   ####### NO TENEMOS PERMISOS
    #AL IGUAL QUE CON HOSTS LO PRIMERO QUE DEBEMOS HACER ES EXTRAER EL ARCHIVO haproxy.cfg DE lb.qcow2
    call(["sudo virt-copy-out -a /mnt/tmp/auto-p2/lb.qcow2 /etc/haproxy/haproxy.cfg /mnt/tmp/auto-p2"], shell=True)

    #AHORA PROCEDEMOS A MODIFICAR SU CONTENIDO
    f1=open("/mnt/tmp/auto-p2/haproxy.cfg","r")
    f2=open("/mnt/tmp/auto-p2/dir_for_permissions/haproxy.cfg",'w')

    for line in f1:
        f2.write(line)

    f2.write("\nfrontend lb\n")
    f2.write("\tbind *:80\n")
    f2.write("\tmode http\n")
    f2.write("\tdefault_backend webservers\n\n")

    f2.write("backend webservers\n")
    f2.write("\tmode http\n")
    f2.write("\tbalance roundrobin\n")
    for i in range(1, numero_de_servidores+1):
        n = str(i)
        f2.write("\tserver s"+ n +" 10.0.2.1"+ n +":80 check\n")

    f2.close()
    f1.close()

    #UNA VEZ MODIFICADO VOLVEMOS A INTRODUCIRLO EN /etc/haproxy DE lb.qcow2
    call(["sudo virt-copy-in -a /mnt/tmp/auto-p2/lb.qcow2 /mnt/tmp/auto-p2/dir_for_permissions/haproxy.cfg /etc/haproxy"], shell=True)  

#################     FINAL LB      #######################

#################     SERVIDORES      #######################
    
    #procedemos a crear todos los archivos para los servidores de la misma forma que hemos hecho con c1 y lb
    #los creamos con un bucle for para automatizar el proceso.
    for i in range(1,numero_de_servidores+1):
        n = str(i)

        # Creacion de la imagen y del xml del servidor a partir de las plantillas.
        call(["qemu-img create -f qcow2 -b "+ cwd +"/cdps-vm-base-pc1.qcow2 /mnt/tmp/auto-p2/s" + n +".qcow2"], shell=True)
        call(["cp "+ cwd +"/plantilla-vm-pc1.xml /mnt/tmp/auto-p2/s" + n +".xml"], shell=True)

        #CREACION DE Sn.XML
        plantilla=open(cwd +"/plantilla-vm-pc1.xml",'r')
        xml=open("/mnt/tmp/auto-p2/s" + n +".xml",'w')

        for line in plantilla:
            if "<name>XXX</name>" in line:
                xml.write(line.replace("XXX", "S" + n))
            elif "/mnt/tmp/XXX/XXX.qcow2" in line:
                xml.write(line.replace("/mnt/tmp/XXX/XXX", "/mnt/tmp/auto-p2/s" + n))
            elif "<source bridge=\"XXX\"/>" in line:  #hace falta escapar las comillas
                xml.write(line.replace("XXX", "LAN2"))
            else:
                xml.write(line) 
        xml.close()
        plantilla.close()

        # Creacion del archivo de configuracion hostname del servidor.
        call(["echo s"+ n +" > /mnt/tmp/auto-p2/hostname_s" + n ], shell=True)

        # Creacion del archivo de configuracion de red (interfaces) del servidor.
        f=open("/mnt/tmp/auto-p2/interfaces_s"+ n ,'w')
        f.write("auto lo\n")
        f.write("iface lo inet loopback\n")
        f.write("auto eth0\n")
        f.write("iface eth0 inet static\n")
        f.write("\taddress 10.0.2.1"+n+"\n")
        f.write("\tnetmask 255.255.255.0\n")
        f.write("\tgateway 10.0.2.1\n")
        f.write("\tdns-nameservers 10.0.2.1")
        f.close()

        #Vamos a realizar la configuracion de red de los servidores de forma permanente.
        #Copia de los archivos de configuracion de sn del directorio temporal del host a la maquina virtual.
        #INTERFACES
        call(["cp /mnt/tmp/auto-p2/interfaces_s"+ n +" /mnt/tmp/auto-p2/interfaces"], shell=True)
        call(["sudo virt-copy-in -a /mnt/tmp/auto-p2/s"+ n +".qcow2 /mnt/tmp/auto-p2/interfaces /etc/network"], shell=True)
        #HOSTNAME
        call(["cp /mnt/tmp/auto-p2/hostname_s"+ n +" /mnt/tmp/auto-p2/hostname"], shell=True) 
        call(["sudo virt-copy-in -a /mnt/tmp/auto-p2/s"+ n +".qcow2 /mnt/tmp/auto-p2/hostname /etc"], shell=True)

        #PARA MODIFICAR EL ARCHIVOS HOSTS PRIMERO DEBEMOS EXTRAERLO DE LA MAQUINA VIRTUAL 
        call(["sudo virt-copy-out -a /mnt/tmp/auto-p2/s"+ n +".qcow2 /etc/hosts /mnt/tmp/auto-p2"], shell=True)
        #AHORA LO PODEMOS EDITAR
        original_hosts=open("/mnt/tmp/auto-p2/hosts",'r')
        nuevo_hosts=open("/mnt/tmp/auto-p2/dir_for_permissions/hosts",'w')
        for line in original_hosts:
            if "127.0.1.1" in line:
                nuevo_hosts.write("127.0.1.1 s"+ n +"\n")
            else:
                nuevo_hosts.write(line)
        original_hosts.close()
        nuevo_hosts.close()

        #UNA VEZ MODIFICADO VOLVEMOS A INTRODUCIRLO EN /etc/haproxy DE sn.qcow2
        call(["sudo virt-copy-in -a /mnt/tmp/auto-p2/s"+ n +".qcow2 /mnt/tmp/auto-p2/dir_for_permissions/hosts /etc"], shell=True)

        call(["echo S"+n+" > /mnt/tmp/auto-p2/index.html"], shell=True)
        call(["sudo virt-copy-in -a /mnt/tmp/auto-p2/s"+n+".qcow2 /mnt/tmp/auto-p2/index.html /var/www/html"], shell=True)
    
    
#################     FINAL SERVIDORES      #######################


################ CREACION DE BRIDGES Y DEFINICION DE DOMINIOS #####################

    #CREA DOS NUEVOS BRIDGES LLAMADOS LAN1 Y LAN2
    call(["sudo brctl addbr LAN1"], shell=True)
    call(["sudo brctl addbr LAN2"], shell=True)
    call(["sudo ifconfig LAN1 up"], shell=True)
    call(["sudo ifconfig LAN2 up"], shell=True)

    #DEFINICION DE DOMINIOS
    call(["sudo virsh define /mnt/tmp/auto-p2/c1.xml"], shell=True)                   #C1
    call(["sudo virsh define /mnt/tmp/auto-p2/lb.xml"], shell=True)                   #LB
    for i in range(1,numero_de_servidores+1):
        n = str(i)
        call(["sudo virsh define /mnt/tmp/auto-p2/s" + n +".xml"], shell=True)        #Sn

#################     HOST      #######################
    call(["sudo ifconfig LAN1 10.0.1.3/24"], shell=True)            #configuracion IP
    call(["sudo ip route add 10.0.0.0/16 via 10.0.1.1"],shell=True) #direccion IP por defecto del host para conectarse a la red virtual
#################     FINAL HOST      #######################






def launch():

    #recogemos del json el numero de servidores que debemos arrancar
    with open('/mnt/tmp/auto-p2/auto-p2.json') as file:
        data = json.load(file)

    numero_de_servidores = int(data['num_serv'])

    #Mira la cantidad de argumentos para saber si se ha introducido una MV especifico (ocurre cuando hay un segundo argumento). Si lo hay solo se arrancara el indicado.    
    if len(sys.argv) == 3:
        maquina_especifica = str(sys.argv[2]).lower()
        for i in range(1,numero_de_servidores+1):
            n = str(i)
            if maquina_especifica == "s"+ n:
                call(["sudo virsh start S" + n], shell=True)
                call(["xterm -rv -sb -rightbar -fa  monospace -fs  10 -title  's"+ n +"' -e  'sudo virsh console S" + n +"'&"], shell=True)
                sys.exit()  # para que una vez encuentre la maquina deseada termine el programa

        if maquina_especifica == "c1":
            call(["sudo virsh start C1"], shell=True)
            call(["xterm -rv -sb -rightbar -fa  monospace -fs  10 -title  'c1\' -e  'sudo virsh console C1\'&"], shell=True)

        elif maquina_especifica == "lb":
            call(["sudo virsh start LB"], shell=True)
            call(["xterm -rv -sb -rightbar -fa  monospace -fs  10 -title  'lb\' -e  'sudo virsh console LB\'&"], shell=True)
                
        else:
            # Si la MV indicada en el segundo argumento no se corresponde con ninguna se muestra por pantalla el siguiente:
            print("El nombre introducido en el segundo argumento no se corresponde con el de ninguna maquina virtual. Debe introducir valor correcto o no introducir nada en el segundo argumento.")
            sys.exit()

    # Si no se ha introducido este argumento se arrancan todas las MV
    else:
        # Arranca C1 y abrimos un terminal con su maquina virtual
        call(["sudo virsh start C1"], shell=True)
        call(["xterm -rv -sb -rightbar -fa  monospace -fs  10 -title  'c1\' -e  'sudo virsh console C1\'&"], shell=True)

        # Arranca LB y abrimos un terminal con su maquina virtual
        call(["sudo virsh start LB"], shell=True)
        call(["xterm -rv -sb -rightbar -fa  monospace -fs  10 -title  'lb\' -e  'sudo virsh console LB\'&"], shell=True)

       # Arranca Sn y abrimos un terminal con su maquina virtual
        for i in range(1,numero_de_servidores+1): 
            n = str(i)
            call(["sudo virsh start S" + n], shell=True)
            call(["xterm -rv -sb -rightbar -fa  monospace -fs  10 -title  's"+ n +"' -e  'sudo virsh console S" + n +"'&"], shell=True)






def stop():
    #recogemos del json el numero de servidores que debemos parar
    with open('/mnt/tmp/auto-p2/auto-p2.json') as file:
        data = json.load(file)

    numero_de_servidores = int(data['num_serv'])
 
    # Mira la cantidad de argumentos para saber si se ha introducido una MV especifico (ocurre cuando hay un segundo argumento). Si lo hay solo se parara el indicado.
    if len(sys.argv) == 3:
        maquina_especifica = str(sys.argv[2]).lower()

        for i in range(1,numero_de_servidores+1):
            n=str(i)
            if maquina_especifica == "s"+n:
                call(["sudo virsh shutdown S"+n], shell=True)
                sys.exit()  # para que una vez encuentre la maquina deseada termine el programa

        if maquina_especifica == "c1":
            call(["sudo virsh shutdown C1"], shell=True)

        elif maquina_especifica == "lb":
            call(["sudo virsh shutdown LB"], shell=True)

        else:
            # Si la MV indicada en el segundo argumento no se corresponde con ninguna se muestra por pantalla el siguiente:
            print("El nombre introducido en el segundo argumento no se corresponde con el de ninguna maquina virtual. Debe introducir valor correcto o no introducir nada en el segundo argumento.")
            sys.exit()

    # Si no se ha introducido este argumento se pararan todas las MV
    else:
        #shutdown apaga nuestro sistema de forma segura
        for i in range(1,numero_de_servidores+1):
            n=str(i)
            call(["sudo virsh shutdown S"+ n ], shell=True)
        
        call(["sudo virsh shutdown C1"], shell=True)
        call(["sudo virsh shutdown LB"], shell=True)
        






def release():
    
    #recogemos del json el numero de servidores que debemos eliminar
    with open('/mnt/tmp/auto-p2/auto-p2.json') as file:
        data = json.load(file)

    numero_de_servidores = int(data['num_serv'])

     #Mediante el comando virsh destroy las MV seran destruidas quedando inactivas
     #Es como quitar la fuente de alimentacion    
    call(["sudo virsh destroy C1"], shell=True)
    call(["sudo virsh destroy LB"], shell=True)
    for i in range(1,numero_de_servidores+1):
        n=str(i)
        call(["sudo virsh destroy S"+ n ], shell=True)

    #La definicion de los dominios seran eliminadas por el comando virsh undefine.
    call(["sudo virsh undefine C1"], shell=True)
    call(["sudo virsh undefine LB"], shell=True)
    for i in range(1,numero_de_servidores+1):
        n=str(i)
        call(["sudo virsh undefine S"+ n ], shell=True)

    # En primer lugar hace dejar de funcionar a las LAN pra despues borrarlas.
    call(["sudo ifconfig LAN1 down"], shell=True)
    call(["sudo ifconfig LAN2 down"], shell=True)
    call(["sudo brctl delbr LAN1"], shell=True)
    call(["sudo brctl delbr LAN2"], shell=True)

    # Para eliminar auto-p2 (donde hemos realizado el trabajo) y todos los archivos que hemos ido creando anteriormente.
    call(["rm -rf /mnt/tmp/auto-p2"], shell=True)





# Informacion comandos virsh: https://libvirt.org/manpages/virsh.html#domstate
def monitor():
    # Utilizamos try-except para poder evitar asique devuelva un error al utilizar ctrl+c para abandonar el metodo monitor.
    try:
        #recogemos del json el numero de servidores que queremos monitorizar 
        with open('/mnt/tmp/auto-p2/auto-p2.json') as file:
            data = json.load(file)
        numero_de_servidores = int(data['num_serv'])

        #DOMINFO
        call(["xterm -rv -sb -rightbar -fa  monospace -fs 10 -title  'Monitor C1\' -e 'watch -n 0.1 sudo virsh dominfo C1 \' &"], shell=True)
        call(["xterm -rv -sb -rightbar -fa  monospace -fs 10 -title  'Monitor LB\' -e 'watch -n 0.1 sudo virsh dominfo LB \' &"], shell=True)
        for i in range (1, numero_de_servidores+1):
            n = str(i)
            call(["xterm -rv -sb -rightbar -fa  monospace -fs 10 -title  'Monitor S"+n+"\' -e 'watch -n 0.1 sudo virsh dominfo S"+n+" \' &"], shell=True)
        #LIST
        call(["xterm -rv -sb -rightbar -fa  monospace -fs 10 -title  'Monitor LIST\' -e 'watch -n 0.1 sudo virsh list --all \' &"], shell=True)
    except KeyboardInterrupt:
        sys.exit()






#ESTA FUNCION SE ENCARGARA DE MODIFICAR EL HAPROXY DE FORMA QUE PODAMOS OTORGAR UN PESO DISTINTO A CADA SERVIDOR
#PARA QUE EL USUARIO TENGA CAPACIDAD DE DECISION SOBRE LA FORMA EN QUE SE REALIZA EL BALANCEO
def balance():
    #recogemos del json el numero de servidores de los que disponemos
    with open('/mnt/tmp/auto-p2/auto-p2.json') as file:
        data = json.load(file)

    numero_de_servidores = int(data['num_serv'])

    #LO PRIMERO QUE DEBEMOS HACER ES COMPROBAR QUE NUMERO DE PESOS QUE HEMOS INTRODUCIDO
    #COINCIDE CON EL NUMERO DE SERVIDORES QUE TENEMOS EN EL ESCENARIO
    #EL NUMERO DE PESOS A OTORGAR SERAN LOS PARAMETROS QUE VENGAN A CONTINUACION DE LA ORDEN
    if (numero_de_servidores+2) == len(sys.argv) :
        #NO HACE FALTA VOLVER A EXTRAER EL FICHERO haproxy.cfg DE lb.qcow2 
        #PODEMOS MODIFICAR DIRECTAMENTE LA COPIA QUE TENIAMOS EN EL DIRECTORIO dir_for_permissions
        #call(["cp /mnt/tmp/auto-p2/dir_for_permissions/haproxy.cfg /mnt/tmp/auto-p2/dir_for_permissions/haproxy_copia.cfg"], shell=True)
        f1=open("/mnt/tmp/auto-p2/dir_for_permissions/haproxy.cfg",'r')
        f2=open("/mnt/tmp/auto-p2/dir_for_permissions/haproxy_copia.cfg",'w')

        #comprobamos que la cadena solo contiene numeros enteros positivos
        for x in range (2,numero_de_servidores+2):
            if str(sys.argv[x]).isdigit()==False:
                print("Lo sentimos. Alguno de los pesos que desea dar no es un numero valido")
                sys.exit()

        for i in range (1, numero_de_servidores+1):
            for line in f1:
                n = str(i)
                peso = str(sys.argv[i+1])
                if "server s"+n+" 10.0.2.1"+n+":80 check" in line:
                    f2.write("\tserver s"+n+" 10.0.2.1"+n+":80 check weight "+peso+"\n")
                    break
                else:
                    f2.write(line)

        f1.close()
        f2.close()

        call(["cp /mnt/tmp/auto-p2/dir_for_permissions/haproxy_copia.cfg /mnt/tmp/auto-p2/dir_for_permissions/haproxy.cfg"], shell=True)
        #YA TENEMOS MODIFICADO EL FICHERO
        #UNA VEZ MODIFICADO VOLVEMOS A INTRODUCIRLO EN /etc/haproxy DE lb.qcow2
        call(["sudo virt-copy-in -a /mnt/tmp/auto-p2/lb.qcow2 /mnt/tmp/auto-p2/dir_for_permissions/haproxy.cfg /etc/haproxy"], shell=True)  
        
        #FINALMENTE REARRANCAMOS HAproxy
        #call(["sudo service haproxy restart"], shell=True)      ############# NO PUEDO PORQUE NO TENEMOS PERMISOS DE ADMINISTRADOR
    
    else:
        print("La cantidad de pesos que ha introducido no coincide con los servidores disponibles")
        sys.exit()

############################################################################

if orden=="prepare":
    prepare()
elif orden=="launch":
    launch()
elif orden=="stop":
    stop()
elif orden=="release":
    release()
elif orden=="monitor":
    monitor()
elif orden=="balance": #llamar a la funcion antes de arrancar las maquinas virtuales
    balance()
else:
    print("Por favor, debe introducir una orden valida.")
    sys.exit()
