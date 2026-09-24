#$ Greatest common divisor of two numbers (Euclid's algorithm) #$
def main_gcd():
#{
    #declare a, b, r
    a = int(input());
    b = int(input());
    while (b != 0):
    #{
        r = a - (a // b) * b;
        a = b;
        b = r;
    #}
    print(a);
#}
if __name__ == "__main__":
    main_gcd();
