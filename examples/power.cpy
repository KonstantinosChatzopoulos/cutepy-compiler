#$ Recursive exponentiation with a local function #$
def main_power():
#{
    #declare base, n
    def power(b, e):
    #{
        if (e == 0):
            return (1);
        return (b * power(b, e - 1));
    #}
    base = int(input());
    n = int(input());
    print(power(base, n));
#}
if __name__ == "__main__":
    main_power();
