from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
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
    return 'Modulo Inventario'

@app.route('/productos')
def get_products():
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM producto')
    productos_obt  =  cur.fetchall()
    productos_resp = []
    for producto in productos_obt:
        producto_dict = {"idProducto":producto[0], "nombre":producto[1], "descripcion":producto[2], "precio_unitario":producto[3], "stock":producto[4], "idCategoria_producto":producto[5], "marca":producto[6], "capacidad":producto[7]}
        productos_resp.append(producto_dict)

    return jsonify({'productos':productos_resp})

@app.route('/producto/<id>')
def get_product(id):
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM producto WHERE idProducto = %s',[id])
    producto = cur.fetchone()
    if producto :
        return jsonify({"producto":{"idProducto":producto[0], "nombre":producto[1], "descripcion":producto[2], "precio_unitario":producto[3], "stock":producto[4], "idCategoria_producto":producto[5], "marca":producto[6], "capacidad":producto[7]}})
    else:
        return jsonify({"mensaje":"producto no encontrado"})

@app.route('/productos/busqueda/<texto>')
def search_products(texto):

    texto = texto.strip()
    print(texto)

    cur = mysql.connection.cursor()
    query = "SELECT * FROM producto WHERE nombre LIKE '%" +texto +"%' OR descripcion LIKE '%"+texto+"%' OR marca LIKE '%"+texto+"%';"
    print(query)
    cur.execute(query)
    productos_obt  =  cur.fetchall()
    productos_resp = []
    print(productos_obt)
    if productos_obt:
        for producto in productos_obt:
            producto_dict = {"idProducto":producto[0], "nombre":producto[1], "descripcion":producto[2], "precio_unitario":producto[3], "stock":producto[4], "idCategoria_producto":producto[5], "marca":producto[6], "capacidad":producto[7]}
            productos_resp.append(producto_dict)

        return jsonify({'productos':productos_resp})
    else:
        return jsonify({'mensaje':'No se encontraron productos que coincidan con {}'.format(texto)})

@app.route('/productos',methods=['POST'])
def add_product():
    if request.method == 'POST':
        new_product = {
            # "idProducto": request.json['idProducto'],
            "nombre": request.json['nombre'],
            "descripcion": request.json['descripcion'],
            "precio_unitario": request.json['precio_unitario'],
            "stock": request.json['stock'],
            "idCategoria_producto": request.json['idCategoria_producto'],
            "marca": request.json['marca'],
            "capacidad": request.json['capacidad']
        }

        try:
            cur = mysql.connection.cursor()
            cur.execute("""INSERT INTO producto ( nombre, descripcion, precio_unitario, stock, idCategoria_producto, marca, capacidad) VALUES (%s, %s, %s,  %s, %s, %s, %s)""",
            (new_product['nombre'], new_product['descripcion'], 
            new_product['precio_unitario'], new_product['stock'], new_product['idCategoria_producto'], 
            new_product['marca'], new_product['capacidad']))
        
            mysql.connection.commit()
            return jsonify({"mensaje": "Producto agregado satisfactoriamente"})
        except Exception as e:
            print(e)
            return jsonify({"mensaje": "Algo salió mal"})

@app.route('/productos/<int:id>', methods=['PUT'])
def update_product(id):
    
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM producto WHERE idProducto = %s',[id])
    producto = cur.fetchone()
    if not producto :
        return jsonify({"mensaje":"producto no encontrado"})
    else:
        try:
            datos=[]
            query = """UPDATE producto
                SET """
            
            # print(request.json)
            # print(type(request.json))

            for key, val in request.json.items():
                query+= key + "=%s,"
                datos.append(val)
            query = query[:-1]
            query += " WHERE idProducto= %s"

            datos.append(id)
            datos_tupla = tuple(datos)

            # print("query:",query)
            # print("datos:",datos_tupla)
            cur = mysql.connection.cursor()
            cur.execute(query, datos_tupla)
        
            mysql.connection.commit()

            return jsonify({"mensaje": "Producto actualizado satisfactoriamente"})
        except Exception as e:
            print(e)
            return jsonify({"mensaje": "Algo salió mal"})


## SECCIÓN USUARIOS

#verificar existe usuario para login
@app.route('/usuario',methods=['POST'])
def verificar_usuario():
    if request.method == 'POST':
        usuario = {
            "user":request.json['user'],
            "password":request.json['password']
        }
        print(usuario)

        try:
            cur = mysql.connection.cursor()
            script_select = "SELECT * FROM usuario WHERE user = '{}' AND password = '{}';".format(usuario['user'],usuario['password'])
            print("script_select: ",script_select)
            cur.execute(script_select)
            usuario_encontrado = cur.fetchone()

            if not usuario_encontrado :
                return jsonify({"mensaje":"usuario no encontrado","acceso":"no"})
            else:
                return jsonify({"mensaje": "usuario encontrado","acceso":"si"})
        except Exception as e:
            print(e)
            return jsonify({"mensaje": "Algo salió mal"})

if __name__ == '__main__':
    app.run(port=3000, debug=True)