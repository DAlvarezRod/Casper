import string
import unicodedata

# "def" define una funcion: nos ayuda a tener multiples funciones
# que podemos usar despues en varias partes del codigo.
# Separacion de Responsabilidades: no se trata de que una funcion
# solo haga una linea, sino de que una funcion no haga TODO.


def strip_accents(text):
    # NFD descompone un caracter acentuado como "e" en dos partes:
    # la letra base "e" + la marca de acento combinada.
    # unicodedata.combining() detecta esas marcas, asi que nos
    # quedamos solo con las letras base.
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def normalize_text(text):
    # .lower() pasa el input a minusculas.
    # .strip() elimina los espacios al inicio y al final.
    text = text.lower().strip()
    # Quitamos los acentos ANTES de comparar con los comandos,
    # asi "Quien eres?" coincide con "quien eres".
    text = strip_accents(text)
    punctuation = string.punctuation + "¿¡"
    table = str.maketrans("", "", punctuation)
    text = text.translate(table)
    return text


def process_message(message):
    # return devuelve un valor a quien llamo la funcion.
    if message == "salir":
        return "salir"
    elif message == "hola":
        return "Hola. ¿En que puedo ayudarte?"
    elif message == "quien eres":
        return "Soy Casper, tu asistente personal"
    else:
        return "Todavia no se como responder a eso"


def main():
    print("Casper iniciado.")
    print("Escribe 'salir' para terminar.")

    while True:
        user_input = input("Tu: ")
        message = normalize_text(user_input)
        response = process_message(message)

        if response == "salir":
            print("Casper: Hasta luego.")
            break

        print("Casper:", response)


if __name__ == "__main__":
    # __name__ vale "__main__" cuando ejecutamos este archivo directamente.
    main()
