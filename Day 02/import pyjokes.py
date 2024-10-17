import pyjokes

def tell_joke():
    joke = pyjokes.get_joke()
    print("Here's a joke for you:")
    print(joke)

tell_joke()