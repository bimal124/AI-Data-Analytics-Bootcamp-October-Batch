# operations.py

class Calculator: # inside class calculator, we define method add

    def add(self, a, b): # The first parameter is self, which refers to the instance of the class.
    #  self allows methods within the class to access the object’s attributes and other methods   
        """Return the sum of two numbers."""
        return a + b
    
    #The method add(self, a, b) belongs to the class Calculator, but we use it with an object (calc), which passes itself (self) to access the method.
    # calc = Calculator()  # `calc` is an object of the Calculator class 


    def subtract(self, a, b): 
        """Return the difference of two numbers."""
        return a - b

