#$ Nested functions that read variables of enclosing functions #$
def main_nested():
#{
    #declare limit, total
    def sumTo(n):
    #{
        #declare i, acc
        def step(k):
        #{
            if ([k <= limit] and not [k == 0]):
                return (k);
            return (0);
        #}
        acc = 0;
        i = 1;
        while (i <= n):
        #{
            acc = acc + step(i);
            i = i + 1;
        #}
        return (acc);
    #}
    limit = 5;
    total = sumTo(10);
    print(total);
#}
if __name__ == "__main__":
    main_nested();
