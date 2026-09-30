import string

"""
El def es para definir una función. Nos ayuda para tener múltiples funciones que podemos 
usar después en varias partes del código.
"""
"""
Separación de Responsabilidades:
No se trata de que una función solo haga una línea, sino que una función no haga todo. 
"""

def normalize_text(text):
    text = text.lower().strip()
    punctuation = string.punctuation + "¿¡"
    table = str.maketrans("","", punctuation)
    text = text.translate(table)
    return text

def process_message(message):
    if message == "salir":
        return "salir"
    elif message == "hola":
        return "Hola. ¿En que puedo ayudarte?"
    elif message == "quien eres":
        return "Soy Casper, tu asistente personal"
    else:
        return "Todavia no se como responder a eso"
# El return hace que la función devuelva un valor a quien la llamó. 

"""
Con el .lower() hacemos que el input del usuario pase a minuscula.
Con el .strip() hacemos que los espacios que se encuentren al inicio y al final en el input del usuario desaparezcan.
Con el .rstrip() hacemos que Python elimine los carácteres mencionados del final de la cadena si aparecen allí.
"""
    
def main():
    print("Casper iniciado.")
    print("Escribe 'salir' para terminar.")

    while True:
        user_input = input("Tu: ")
        # Se aplica la normalización de texto
        message = normalize_text(user_input)
        response = process_message(message)

        if response == "salir":
            print("Casper: Hasta luego.")
            break

        print("Casper:", response) 

if __name__=="__main__":
    main()
# __name__ tiene el valor de __main__. El __name__ es una variable específica de Python. 
