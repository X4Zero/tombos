from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from dateutil import tz
from datetime import datetime

app = Flask(__name__)

# Mysql connection
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'tombos'

# settings
app.secret_key = 'mysecretkey'

mysql = MySQL(app)


@app.route('/')
def index():
    return 'Modulo Ventas'
    
# Proformas
@app.route('/proformas')
def obtener_proformas():
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM proforma')
    proformas_obt  =  cur.fetchall()
    proformas_resp = []
    if proformas_obt :
        for proforma in proformas_obt:
            proforma_dict = {"idProforma":proforma[0], "fecha":proforma[1], "total":proforma[2], "idCliente":proforma[3]}
            
            cur.execute('SELECT * FROM producto_has_proforma WHERE proforma_idproforma=%s',[proforma[0]])
            detalles_obt = cur.fetchall()
            detalles_resp = []
            for detalle in detalles_obt:
                detalle_dict = {"idProducto":detalle[0],"idProforma":detalle[1],"cantidad":detalle[2],"subtotal":detalle[3]}
                detalles_resp.append(detalle_dict)
            proforma_dict["detalle"]=detalles_resp
            proformas_resp.append(proforma_dict)

        return jsonify({'proformas':proformas_resp})
    else:
        return jsonify({'mensaje':'No hay proformas'})

@app.route('/proformas/<id>')
def obtener_proforma(id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM proforma WHERE idproforma = %s',[id])
    proforma = cur.fetchone()
    if proforma :
        cur.execute('SELECT * FROM producto_has_proforma WHERE proforma_idproforma=%s',[factura[0]])
        detalles_obt = cur.fetchall()
        detalles_resp = []
        for detalle in detalles_obt:
            detalle_dict = {"idProducto":detalle[0],"idProforma":detalle[1],"cantidad":detalle[2],"subtotal":detalle[3]}
            detalles_resp.append(detalle_dict)

        return jsonify({"proforma":{"idProforma":proforma[0], "fecha":proforma[1], "total":proforma[2], "idCliente":proforma[3],"detalle":detalles_resp}})
    else:
        return jsonify({"mensaje":"proforma no encontrada"})

@app.route('/proformas', methods=['POST'])
def crear_proforma():
    if request.method == 'POST':
        ids = request.json['ids']
        cantidades = request.json['cantidades']
        id_cliente = request.json['idCliente']
        # Primero se crea la proforma en la bd
       
        ## Obtenemos los datos de los productos
        productos_ids = [str(id) for id in ids]
        productos_ids = ','.join(productos_ids)
        # print(productos_ids)

        es_valido=True
        total_proforma=0
    
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM producto WHERE idProducto in ('+productos_ids+')')
        productos_obt  =  cur.fetchall()
        productos_resp = []
        for producto in productos_obt:
            producto_dict = {"idProducto":producto[0], "nombre":producto[1], "descripcion":producto[2], "precio_unitario":producto[3], "stock":producto[4], "idCategoria_producto":producto[5], "marca":producto[6], "capacidad":producto[7]}
            productos_resp.append(producto_dict)

        for producto in productos_resp:
            indice_producto = ids.index(producto['idProducto'])
            if cantidades[indice_producto] <= producto['stock']:
                producto['cantidad'] = cantidades[indice_producto]
                producto['subtotal'] = producto['cantidad'] * producto['precio_unitario']
                total_proforma+=producto['subtotal'] # obtenemos el total
            else:
                es_valido = False
                break
        
        if not es_valido:
            return jsonify({'mensaje':'no hay stock suficiente'})
        
        try:
            ## Luego se llena el detalle de la proforma
            #### Para factura necesitamos idcliente, total, fecha
            print('query_factura: ','INSERT INTO proforma (fecha, total, cliente_idcliente) VALUES (CURDATE(), %s, %s)',
            (total_proforma,id_cliente))
            cur.execute('INSERT INTO proforma (fecha, total, cliente_idcliente) VALUES (CURDATE(), %s, %s)',
            (total_proforma,id_cliente))
            mysql.connection.commit()
            

            ## Obtenemos id de la factura que insertamos
            cur.execute('SELECT MAX(idproforma) FROM proforma;')
            proforma  =  cur.fetchone()
            id_proforma=proforma[0]

            ## Insertamos en detalle_factura: idproducto, idfactura, cantidad, subtotal
            detalle_productos = ''
            # id_factura=2
            for producto in productos_resp:
                detalle_productos+="({},{},{},{}),".format(producto['idProducto'],id_proforma,producto['cantidad'],producto['subtotal'])
            detalle_productos=detalle_productos[:-1]
            # print(detalle_productos)

            query_detalle = 'INSERT INTO producto_has_proforma (Producto_idProducto, proforma_idproforma, cantidad, subtotal) VALUES '+detalle_productos+';'
            print('query_detalle: ',query_detalle)
            cur.execute(query_detalle)
            mysql.connection.commit()
        
        except Exception as e:
            print(e)
            return jsonify({"mensaje": "Algo salió mal"})

        return jsonify({'mensaje': 'Se ha creado con éxito la proforma N° {} '.format(id_proforma)})

@app.route('/proforma_factura/<id>', methods=['POST'])
def gen_factura_de_proforma(id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM proforma WHERE idproforma = %s',[id])
    proforma = cur.fetchone()
    if proforma :
        # Obtenemos los datos de la proforma
        cur.execute('SELECT * FROM producto_has_proforma WHERE proforma_idproforma=%s',[proforma[0]])
        detalles_obt = cur.fetchall()
        detalles_resp = []

        ids_productos = []# ids de los productos
        for detalle in detalles_obt:
            detalle_dict = {"idProducto":detalle[0],"idProforma":detalle[1],"cantidad":detalle[2],"subtotal":detalle[3]}
            ids_productos.append(detalle[0])
            detalles_resp.append(detalle_dict)

        # Obtenemos el stock de los productos
        ids_productos = [str(id) for id in ids_productos]
        ids_ins = ','.join(ids_productos)

        query = "SELECT * FROM producto  WHERE idProducto IN ("+ids_ins+");"
        print('query: ',query)
        cur.execute(query)
        productos_obt = cur.fetchall()
        productos_resp = []

        ## Verificamos el stock
        for producto in productos_obt:
            producto_dict = {"idProducto":producto[0], "stock":producto[4]}

            for detalle in detalles_resp:
                if producto_dict["idProducto"] == detalle["idProducto"]:
                    # print(producto_dict["stock"],detalle["cantidad"])
                    if producto_dict["stock"]-detalle["cantidad"]<0:
                        return jsonify({"mensaje":"No hay stock suficiente"})
                    else:
                        producto_dict["cantidad"] = detalle["cantidad"]
            
            productos_resp.append(producto_dict)

        ## Creamos la nuva factura con los datos de la proforma
        query_insert = 'INSERT INTO factura (fecha, total, cliente_idcliente) SELECT fecha, total, cliente_idcliente  FROM proforma WHERE idproforma={};'.format(id)
        print('query_insert:',query_insert)
        cur.execute(query_insert)
        mysql.connection.commit()

        ## Obtenemos el numero de la factura
        cur.execute('SELECT MAX(idFactura) FROM factura;')
        factura  =  cur.fetchone()
        id_factura=factura[0]

        ## Insertammos en detalle de factura desde detalle de proforma
        query_insert_ = 'INSERT INTO detalle (Producto_idProducto, Factura_idFactura,cantidad,subtotal) SELECT producto_idProducto, {}, cantidad, subtotal FROM producto_has_proforma WHERE proforma_idproforma={};'.format(id_factura,id)
        print('query_insert: ',query_insert_)
        cur.execute(query_insert_)

        ## Actualizamos stock en tabla producto
        for producto in productos_resp:
            query_update = 'UPDATE producto SET stock = {} WHERE idProducto = {}'.format(producto['stock']-producto['cantidad'], producto['idProducto'])
            print('query_update: ' , query_update)
            cur.execute(query_update)
            mysql.connection.commit()

        return jsonify({"mensaje":"Se ha creado con éxito la factura N° {} a partir de la proforma N° {}".format(id_factura,id)})
    else:
        return jsonify({"mensaje":"proforma no encontrada"})
    
# Fin Proformas



# Facturas
@app.route('/facturas')
def obtener_facturas():
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM factura')
    facturas_obt  =  cur.fetchall()
    facturas_resp = []
    for factura in facturas_obt:
        factura_dict = {"idFactura":factura[0], "fecha":factura[1], "total":factura[2], "idCliente":factura[3]}
        
        cur.execute('SELECT * FROM detalle WHERE Factura_idFactura=%s',[factura[0]])
        detalles_obt = cur.fetchall()
        detalles_resp = []
        for detalle in detalles_obt:
            detalle_dict = {"idProducto":detalle[0],"idFactura":detalle[1],"cantidad":detalle[2],"subtotal":detalle[3]}
            detalles_resp.append(detalle_dict)
        factura_dict["detalle"]=detalles_resp
        facturas_resp.append(factura_dict)

    return jsonify({'facturas':facturas_resp})

@app.route('/facturas/<id>')
def obtener_factura(id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM factura WHERE idFactura = %s',[id])
    factura = cur.fetchone()
    if factura :
        cur.execute('SELECT * FROM detalle WHERE Factura_idFactura=%s',[factura[0]])
        detalles_obt = cur.fetchall()
        detalles_resp = []
        for detalle in detalles_obt:
            detalle_dict = {"idProducto":detalle[0],"idFactura":detalle[1],"cantidad":detalle[2],"subtotal":detalle[3]}
            detalles_resp.append(detalle_dict)

        return jsonify({"factura":{"idFactura":factura[0], "fecha":factura[1], "total":factura[2], "idCliente":factura[3],"detalle":detalles_resp}})
    else:
        return jsonify({"mensaje":"factura no encontrada"})

@app.route('/facturas', methods=['POST'])
def crear_factura():
    if request.method == 'POST':
        ids = request.json['ids']
        cantidades = request.json['cantidades']
        id_cliente = request.json['idCliente']
        # Primero se crea la factura en la bd
       
        ## Obtenemos los datos de los productos
        productos_ids = [str(id) for id in ids]
        productos_ids = ','.join(productos_ids)
        # print(productos_ids)

        es_valido=True
        total_factura=0
    
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM producto WHERE idProducto in ('+productos_ids+')')
        productos_obt  =  cur.fetchall()
        productos_resp = []
        for producto in productos_obt:
            producto_dict = {"idProducto":producto[0], "nombre":producto[1], "descripcion":producto[2], "precio_unitario":producto[3], "stock":producto[4], "idCategoria_producto":producto[5], "marca":producto[6], "capacidad":producto[7]}
            productos_resp.append(producto_dict)

        for producto in productos_resp:
            indice_producto = ids.index(producto['idProducto'])
            if cantidades[indice_producto] <= producto['stock']:
                producto['cantidad'] = cantidades[indice_producto]
                producto['subtotal'] = producto['cantidad'] * producto['precio_unitario']
                total_factura+=producto['subtotal'] # obtenemos el total
            else:
                es_valido = False
                break
        
        if not es_valido:
            return jsonify({'mensaje':'no hay stock suficiente'})
        
        try:
            ## Luego se llena el detalle de la factura
            #### Para factura necesitamos idcliente, total, fecha
            cur.execute('INSERT INTO factura (fecha, total, cliente_idcliente) VALUES (CURDATE(), %s, %s)',
            (total_factura,id_cliente))
            mysql.connection.commit()
            print('query_factura: ','INSERT INTO factura (fecha, total, cliente_idcliente) VALUES (CURDATE(), %s, %s)',
            (total_factura,id_cliente))

            ## Obtenemos id de la factura que insertamos
            cur.execute('SELECT MAX(idFactura) FROM factura;')
            factura  =  cur.fetchone()
            id_factura=factura[0]

            ## Insertamos en detalle_factura: idproducto, idfactura, cantidad, subtotal
            detalle_productos = ''
            # id_factura=2
            for producto in productos_resp:
                detalle_productos+="({},{},{},{}),".format(producto['idProducto'],id_factura,producto['cantidad'],producto['subtotal'])
            detalle_productos=detalle_productos[:-1]
            # print(detalle_productos)

            query_detalle = 'INSERT INTO detalle (Producto_idProducto, Factura_idFactura, cantidad, subtotal) VALUES '+detalle_productos+';'
            print('query_detalle: ',query_detalle)
            cur.execute(query_detalle)
            mysql.connection.commit()


            ## Disminuimos el stock en productos
            for producto in productos_resp:
                query_update = 'UPDATE producto SET stock = {} WHERE idProducto = {}'.format(producto['stock']-producto['cantidad'], producto['idProducto'])
                print('query_update: ' , query_update)
                cur.execute(query_update)
                mysql.connection.commit()
        
        except Exception as e:
            print(e)
            return jsonify({"mensaje": "Algo salió mal"})

        return jsonify({'mensaje': 'Se ha creado con éxito la factura N° {} '.format(id_factura)})

# Fin Facturas



# Clientes
@app.route('/clientes')
def get_clients():
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM cliente')
    clientes_obt  =  cur.fetchall()
    clientes_resp = []
    for cliente in clientes_obt:
        cliente_dict = {"idcliente":cliente[0], "nombres":cliente[1], "apellidos":cliente[2], "telefono":cliente[3], "email":cliente[4], "ruc":cliente[5], "direccion":cliente[6], "razon_social":cliente[7]}
        clientes_resp.append(cliente_dict)

    return jsonify({'clientes':clientes_resp})

@app.route('/clientes/<id>')
def get_client(id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM cliente WHERE idcliente = %s',[id])
    cliente = cur.fetchone()
    if cliente :
        return jsonify({"cliente":{"idcliente":cliente[0], "nombres":cliente[1], "apellidos":cliente[2], "telefono":cliente[3], "email":cliente[4], "ruc":cliente[5], "direccion":cliente[6], "razon_social":cliente[7]}})
    else:
        return jsonify({"mensaje":"cliente no encontrado"})

@app.route('/clientes',methods=['POST'])
def add_client():
    if request.method == 'POST':
        new_client = {
            "nombres": request.json['nombres'],
            "apellidos": request.json['apellidos'],
            "telefono": request.json['telefono'],
            "email": request.json['email'],
            "ruc": request.json['ruc'],
            "direccion": request.json['direccion'],
            "razon_social": request.json['razon_social']
        }

        try:
            cur = mysql.connection.cursor()
            cur.execute("""INSERT INTO cliente (nombres,apellidos,telefono,email,ruc,direccion,razon_social) VALUES (%s, %s, %s, %s,  %s, %s, %s)""",
            (new_client['nombres'],
            new_client['apellidos'],
            new_client['telefono'],
            new_client['email'],
            new_client['ruc'], 
            new_client['direccion'],
            new_client['razon_social']))
        
            mysql.connection.commit()
            return jsonify({"mensaje": "Cliente agregado satisfactoriamente"})
        except Exception as e:
            print(e)
            return jsonify({"mensaje": "Algo salió mal"})

# Fin Clientes

if __name__ == '__main__':
    app.run(port=5000, debug=True)