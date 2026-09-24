"""CutePy compiler.

Compiles a program written in CutePy, a small educational Python-like
language, into intermediate code (quads) and RISC-V assembly in one pass.

Usage:
    python compilers.py program.cpy

Output, written to the current directory:
    intermediate code.int   the quads, one per line
    final code.asm          the RISC-V assembly

Sections of this file: final code generation, intermediate code, symbol
table, entry point, parser, lexer.
"""

import sys

# Lexer state
token = ''
family = ''
file_name = ''
current_line = 1
position = 0
legal_symbols = ['+', '-', '*', '/', '=', '<', '>', '!', '(', ')', '[', ']', '{', '}', '#', '$', ',', ';', ':', ' ',
                 '\t', '\n', '_', '"', '']
keywords = ['def', 'not', 'and', 'or', 'if', 'else', 'while', 'return', 'print', 'int', 'input', 'declare']
# Intermediate code
quad_list = []
quad_counter = 0
temp_list = []
temp_counter = 0
# Symbol table (one Scope per nesting level) and final code
depth = 0
myScope = []
parCounter = 0
# Output files
intCode = ''
finCode = ''


#####################################
#   Final code generation (RISC-V)  #
#####################################

def gnvlcode(variable):
    """Emit code that puts in t0 the address of a variable of an enclosing function, following access links."""
    entity, variableNestingLevel = myScope[depth].searchEntity(variable)
    currentLevel = myScope[-1].nestingLevel
    finCode.write('\tlw t0, -4(sp)\n')
    for i in range(currentLevel, int(variableNestingLevel) + 1, -1):
        finCode.write('\tlw t0, -4(t0)\n')
    finCode.write('\taddi t0, t0, -' + str(entity.offset)+'\n')


def loadvr(variable, register):
    """Emit code that loads a constant or a variable into register t<register>."""
    if variable.isdigit():
        finCode.write('\tli t' + str(register) + ', ' + str(variable)+'\n')
    elif variable[0] == '+' or variable[0] == '-':
        temp = variable[1:]
        if temp.isdigit():
            finCode.write('\tli t' + str(register) + ', ' + str(variable)+'\n')
        else:
            print("Error loading an unsigned number to a register in line " + str(current_line) + "!")
            sys.exit(-1)
    else:
        current_level = myScope[-1].nestingLevel
        entity, variableNestingLevel = myScope[current_level].searchEntity(variable)
        # Level 0 (the main function's variables) is addressed from s0, the current level
        # from sp, and enclosing levels through the access links (gnvlcode).
        if int(variableNestingLevel) == 0:
            finCode.write('\tlw t' + str(register) + ', -' + str(entity.offset) + '(s0)\n')
        elif int(variableNestingLevel) == current_level:
            finCode.write('\tlw t' + str(register) + ', -' + str(entity.offset) + '(sp)\n')
        elif int(variableNestingLevel) < current_level:
            gnvlcode(variable)
            finCode.write('\tlw t' + str(register) + ', (t0)\n')
        else:
            print("Error loading a value to a register in line " + str(current_line) + "!")
            sys.exit(-1)


def storerv(register, variable):
    """Emit code that stores register t<register> into a variable."""
    current_level = myScope[-1].nestingLevel
    entity, variableNestingLevel = myScope[current_level].searchEntity(variable)
    if int(variableNestingLevel) == 0:
        finCode.write('\tsw t' + str(register) + ', -' + str(entity.offset) + '(s0)\n')
    elif int(variableNestingLevel) == current_level:
        finCode.write('\tsw t' + str(register) + ', -' + str(entity.offset) + '(sp)\n')
    elif int(variableNestingLevel) < current_level:
        gnvlcode(variable)
        finCode.write('\tsw t' + str(register) + ', (t0)\n')
    else:
        print("Error storing a value in line " + str(current_line) + "!")
        sys.exit(-1)


def generate_final_code(quad):
    """Emit the RISC-V code for one quad, under the label L<quad number>."""
    global parCounter
    operator = quad.getOperator()
    if operator == 'begin_block':
        finCode.write('L'+str(quad.getX())+':\n')
        finCode.write('\tsw ra, (sp)\n')
    # Note: no epilogue (lw ra, (sp) / jr ra) is generated for end_block, so functions
    # don't return to their caller. See "Limitations" in the README.
    elif operator == 'halt':
        finCode.write('L' + str(quad.getCounter()) + ':\n')
        finCode.write('\tli a0, 10\n')
        finCode.write('\tecall\n')
    else:
        finCode.write('L'+str(quad.getCounter())+':\n')
    if operator == 'inp':
        finCode.write('\tli a7, 5\n')
        finCode.write('\tecall\n')
    elif operator == 'out':
        entity, _ =myScope[depth].searchEntity(quad.getX())
        finCode.write('\tlw a0, -'+str(entity.getOffset())+'(gp)\n')
        finCode.write('\tli a7, 1\n')
        finCode.write('\tecall\n')
    elif operator == 'call':
        caller_level = myScope[depth].nestingLevel
        called_entity, called_level = myScope[caller_level].searchEntity(quad.getX())
        # Access link of the new frame: a function at the caller's own level gets the
        # caller's access link; a function nested in the caller gets the caller's frame.
        if caller_level == int(called_level):
            finCode.write('\tlw t0, -4(sp)\n')
            finCode.write('\tsw t0, -4(fp)\n')
        else:
            finCode.write('\tsw sp, -4(fp)\n')
        finCode.write('\taddi sp, sp,'+str(myScope[caller_level].getOffset())+'\n')
        finCode.write('\tjal L'+str(called_entity.getName())+'\n')
        finCode.write('\taddi sp, sp, -'+str(myScope[caller_level].getOffset())+'\n')
        parCounter = 0
    elif operator == 'jump':
        finCode.write('\tj L'+str(quad.getZ())+'\n')
    elif operator == 'retv':
        loadvr(quad.getX(), 1)
        finCode.write('\tlw t0, -8(sp)\n')
        finCode.write('\tsw t1, (t0)\n')
    elif operator == 'par':
        # Before the first parameter, point fp to the frame of the function being called
        # (found by scanning ahead to the call quad). Parameters go to -12, -16, ... of that frame.
        if parCounter == 0:
            i = quad.getCounter()
            while True:
                if quad_list[i].getOperator() == 'call':
                    entity, nestingLevel = myScope[depth].searchEntity(quad_list[i].getX())
                    break
                i += 1
            finCode.write('\taddi fp, sp, '+str(entity.getOffset())+'\n')
        if quad.getY() == 'CV':
            loadvr(quad.getX(), 0)
            finCode.write('\tsw t0, -'+str(12+4*parCounter)+'(fp)\n')
            parCounter += 1
        elif quad.getY() == 'ret':
            entity, nestingLevel = myScope[depth].searchEntity(quad.getX())
            finCode.write('\taddi t0, sp, -' + str(entity.getOffset()) + '\n')
            finCode.write('\tsw t0, -8(fp)\n')
    elif operator == '=':
        loadvr(quad.getX(), 1)
        storerv(1, quad.getZ())
    elif operator == '==' or operator == '!=' or operator == '>=' or operator == '>' or operator == '<=' or operator == '<':
        loadvr(quad.getX(), 1)
        loadvr(quad.getY(), 2)
        if operator == '==':
            branch = 'beq'
        elif operator == '!=':
            branch = 'bne'
        elif operator == '>=':
            branch = 'bge'
        elif operator == '>':
            branch = 'bgt'
        elif operator == '<=':
            branch = 'ble'
        elif operator == '<':
            branch = 'blt'
        finCode.write('\t'+branch+' t1, t2, L'+quad.getZ()+'\n')
    elif operator == '+' or operator == '-' or operator == '*' or operator == '//':
        loadvr(quad.getX(), 1)
        loadvr(quad.getY(), 2)
        if operator == '+':
            op = '	add'
        elif operator == '-':
            op = '	sub'
        elif operator == '*':
            op = '	mul'
        elif operator == '//':
            op = '	div'
        finCode.write(op+' t1, t1, t2\n')
        storerv(1, quad.getZ())


#####################################
#     Intermediate code (quads)     #
#####################################

class quad:
    """One quad of intermediate code: its number, the operator and three operands."""
    def __init__(self, counter, op, x, y, z):
        self.counter = counter
        self.op = op
        self.x = x
        self.y = y
        self.z = z

    def print_quad(self):
        """Write the quad as one line of the .int file."""
        intCode.write(str(self.counter) + " " + str(self.op) + " " + str(self.x) + " " + str(self.y) + " " + str(self.z)+'\n')

    def setz(self, z):
        self.z = z

    def getCounter(self):
        return self.counter

    def getOperator(self):
        return self.op

    def getX(self):
        return self.x

    def getY(self):
        return self.y

    def getZ(self):
        return self.z


def next_quad():
    """Return the number of the next quad to be generated, as a string."""
    return str(quad_counter)


def gen_quad(op, x, y, z):
    """Create a new quad and append it to quad_list."""
    global quad_list
    global quad_counter
    quad_list.append(quad(quad_counter, op, x, y, z))
    quad_counter += 1


def newtemp():
    """Create a temporary variable T_n in the current scope and return its name."""
    global temp_counter
    global depth
    global myScope
    temp_counter += 1
    myScope[depth].addEntity(TemporaryVariable('T_' + str(temp_counter), 'Integer', myScope[depth].nextOffset()))
    return 'T_' + str(temp_counter)


def makelist(x):
    """Return a new list of quad numbers that contains only x."""
    new_list = []
    new_list.append(x)
    return new_list


def merge(list1, list2):
    """Return the two lists of quad numbers joined together."""
    return list1 + list2


def backpatch(list, z):
    """Set z as the jump target of every quad in the list."""
    if (len(list) == 0):
        return
    for x in range(len(list)):
        quad_list[int(list[x])].setz(z)


#####################################
#           Symbol table            #
#####################################

class Scope:
    """One nesting level of the symbol table: its entities and the next free frame offset."""
    def __init__(self, nestingLevel):
        self.nestingLevel = nestingLevel
        self.entityList = []
        # Stack frame layout: 0 = return address (ra), -4 = access link,
        # -8 = address where the return value is stored; variables start at -12.
        self.offset = 12

    def getOffset(self):
        return self.offset

    def nextOffset(self):
        """Reserve the next 4-byte slot of the stack frame and return its offset."""
        offset = self.offset
        self.offset += 4
        return offset

    def addEntity(self, entity):
        """Add a variable, parameter, temporary or function to this scope."""
        self.entityList.append(entity)

    def printEntity(self):
        """Print the scope's entities (for debugging)."""
        print(self.nestingLevel, end='')
        for i in self.entityList:
            i.printEnt()
        print('')

    def setStartingQuad(self, fname, startingQuad):
        """Record the number of the first quad of the function fname."""
        for i in self.entityList:
            if i.getName() == fname:
                i.setStartingQuad(startingQuad)

    def searchEntity(self, name):
        """Find name in this scope or an enclosing one and return (entity, nesting level); exit if it isn't declared."""
        for i in range(self.nestingLevel, -1, -1):
            for entity in myScope[i].entityList:
                if entity.getName() == name:
                    return entity, str(i)
        sys.exit(name + ' is not declared')


class Entity:
    """Base class of all symbol table entries."""
    def __init__(self, name):
        self.name = name

    def getName(self):
        return self.name


class Variable(Entity):
    """A variable with its data type and its offset in the stack frame."""
    def __init__(self, name, datatype, offset):
        super().__init__(name)
        self.datatype = datatype
        self.offset = offset

    def getDatatype(self):
        return self.datatype

    def getOffset(self):
        return self.offset

    def printEnt(self):
        print(' ' + self.getName() + '/' + str(self.getOffset()) + ' ', end='')


class TemporaryVariable(Variable):
    """A temporary variable created by newtemp()."""
    def __init__(self, name, datatype, offset):
        super().__init__(name, datatype, offset)

    def printEnt(self):
        print(' ' + self.getName() + '/' + str(self.getOffset()) + ' ', end='')


class Parameter(Variable):
    """A formal parameter. id_list() also uses it for declared variables."""
    def __init__(self, name, datatype, offset):
        super().__init__(name, datatype, offset)

    def printEnt(self):
        print(' ' + self.getName() + '/' + str(self.getOffset()) + ' ', end='')


class Function(Entity):
    """A local function: its first quad and the frame offset reserved for it in the enclosing scope."""
    def __init__(self, name, datatype):
        super().__init__(name)
        self.datatype = datatype
        self.startingQuad = 0
        self.frameLength = myScope[depth].nextOffset()
        self.parameterList = []

    def getOffset(self):
        return self.frameLength

    def setStartingQuad(self, quadNo):
        self.startingQuad = quadNo

    def printEnt(self):
        print(' ' + self.getName() + '/' + str(self.startingQuad) + '/' + str(self.getOffset()) + ' ', end='')


#####################################
#            Entry point            #
#####################################

def main():
    """Check the command-line argument, open the source and output files, and compile."""
    global file_name
    global intCode
    global finCode
    # Exactly one argument: the source file
    if len(sys.argv) < 2:
        sys.exit("No file for compilation given.")
    elif len(sys.argv) > 2:
        sys.exit('More arguments or files than needed.')
    else:
        # The source file must end in .cpy
        if sys.argv[1][-1] == 'y' and sys.argv[1][-2] == 'p' and sys.argv[1][-3] == 'c' and sys.argv[1][-4] == '.':
            try:
                file_name = open(sys.argv[1], "r")
            except:
                file_name = ''
            if file_name != '':
                intCode = open('intermediate code.int', 'w')
                finCode = open('final code.asm', 'w')
                syntax()
                for x in quad_list:
                    x.print_quad()
            else:
                sys.exit("File " + sys.argv[1] + " not found.")
        else:
            sys.exit('Not supported file type.')


#####################################
#              Parser               #
#####################################
# Recursive descent: one function per grammar rule. The parser also generates the
# quads, fills the symbol table, and emits the final code of each function when its
# block closes (syntax-directed translation, single pass).
# To look ahead, a function saves the file position (tell) and current_line, calls
# lex(), and seeks back if the token belongs to someone else.

def syntax():
    """Start the syntax analysis."""
    startRule()


def startRule():
    """startRule: def_main_part call_main_part"""
    def_main_part()
    call_main_part()


def def_main_part():
    """def_main_part: def_main_function+"""
    def_main_function()
    while peek():
        def_main_function()


def peek() -> bool:
    """Return True if another main function follows; the token is not consumed."""
    global file_name
    global current_line
    line = current_line
    pos = file_name.tell()
    lex()
    if token == 'if':
        current_line = line
        file_name.seek(pos)
        return False
    if token != '':
        file_name.seek(pos)
        current_line = line
        return True
    return False


def peek_fu() -> bool:
    """Return True if a local function declaration follows; the token is not consumed."""
    global file_name
    global current_line
    line = current_line
    pos = file_name.tell()
    lex()
    if token == 'def':
        file_name.seek(pos)
        current_line = line
        return True
    file_name.seek(pos)
    current_line = line
    return False


def def_main_function():
    """def_main_function: 'def' ID '(' ')' ':' '#{' declarations def_function* statements '#}'"""
    global file_name
    global current_line
    line = current_line
    lex()
    global depth
    global myScope
    global parCounter
    # Each main function starts with a new symbol table.
    myScope = []
    depth = 0
    myScope.append(Scope(depth))
    parCounter = 0
    if token == 'def':
        line = current_line
        lex()
        if family == 'identifier':
            if token[0] == 'm' and token[1] == 'a' and token[2] == 'i' and token[3] == 'n' and token[4] == '_':
                line = current_line
                name = token
                lex()
                if token == '(':
                    line = current_line
                    lex()
                    if token == ')':
                        line = current_line
                        lex()
                        if token == ':':
                            line = current_line
                            lex()
                            if token == '#{':
                                declarations()
                                while peek_fu():
                                    def_function()
                                start = int(next_quad())
                                gen_quad('begin_block', name, '_', '_')
                                statements()
                                gen_quad('halt', '_', '_', '_')
                                gen_quad('end_block', name, '_', '_')
                                end = int(next_quad())
                                line = current_line
                                lex()
                                if token == '#}':
                                    # The block is complete, so its quads can be translated.
                                    for i in range(start, end):
                                        generate_final_code(quad_list[i])
                                    return
                                else:
                                    current_line = line
                                    sys.exit('#} expected after statements in line ' + str(current_line))
                            else:
                                current_line = line
                                sys.exit('#{ expected after : in line ' + str(current_line))
                        else:
                            current_line = line
                            sys.exit(': expected after ) in line ' + str(current_line))
                    else:
                        current_line = line
                        sys.exit(') expected after ( in line ' + str(current_line))
                else:
                    current_line = line
                    sys.exit('( expected after main function name in line ' + str(current_line))
            else:
                current_line = line
                sys.exit('Main function is expected to have a main_ like name in line ' + str(current_line))
        else:
            current_line = line
            sys.exit("Keywords can't be used as function names in line " + str(current_line))
    else:
        current_line = line
        sys.exit('def expected for function declaration in line ' + str(current_line))


def def_function():
    """def_function: 'def' ID '(' id_list ')' ':' '#{' declarations def_function* statements '#}'"""
    global file_name
    global current_line
    global depth
    global myScope
    line = current_line
    lex()
    if token == 'def':
        line = current_line
        lex()
        if family == 'identifier':
            if len(token) <= 4 or len(token) > 4 and (
                    token[0] != 'm' or token[1] != 'a' or token[2] != 'i' or token[3] != 'n' or token[4] != '_'):
                myScope[depth].addEntity(Function(token, 'Integer'))
                fname = token
                depth += 1
                myScope.append(Scope(depth))
                line = current_line
                name = token
                lex()
                if token == '(':
                    id_list()
                    line = current_line
                    lex()
                    if token == ')':
                        line = current_line
                        lex()
                        if token == ':':
                            line = current_line
                            lex()
                            if token == '#{':
                                declarations()
                                while peek_fu():
                                    def_function()
                                start = int(next_quad())
                                gen_quad('begin_block', name, '_', '_')
                                myScope[depth - 1].setStartingQuad(fname, len(quad_list))
                                statements()
                                gen_quad('end_block', name, '_', '_')
                                end = int(next_quad())
                                line = current_line
                                lex()
                                if token == '#}':
                                    for i in range(start, end):
                                        generate_final_code(quad_list[i])
                                    # Note: the finished function's scope should be removed here
                                    # (del myScope[-1]). It was disabled while debugging to inspect
                                    # the scopes, so sibling local functions share one scope record.
                                    # See "Limitations" in the README.
                                    depth -= 1
                                    return
                                else:
                                    current_line = line
                                    sys.exit('#} expected after statements in line ' + str(current_line))
                            else:
                                current_line = line
                                sys.exit('#{ expected after : in line ' + str(current_line))
                        else:
                            current_line = line
                            sys.exit(': expected after ) in line ' + str(current_line))
                    else:
                        current_line = line
                        sys.exit(') expected after arguments in line ' + str(current_line))
                else:
                    current_line = line
                    sys.exit('( expected after function name in line ' + str(current_line))
            else:
                current_line = line
                sys.exit('Main function cannot be declared in another main function ' + str(current_line))
        else:
            current_line = line
            sys.exit("Keyword or improper name used as function name in line " + str(current_line))
    else:
        current_line = line
        sys.exit('def expected for function declaration in line ' + str(current_line))


def declarations():
    """declarations: declaration_line*"""
    global file_name
    global current_line
    line = current_line
    pos = file_name.tell()
    lex()
    if token == '#':
        lex()
        if token == 'declare':
            file_name.seek(pos)
            current_line = line
            declaration_line()
            declarations()
        else:
            sys.exit('declare expected after # in declaration in line ' + str(current_line))
    else:
        file_name.seek(pos)
        current_line = line
        return


def declaration_line():
    """declaration_line: '#declare' id_list"""
    global file_name
    global current_line
    lex()
    if token == '#':
        lex()
        if token == 'declare':
            id_list()
        else:
            sys.exit('declare expected after # in declaration in line ' + str(current_line))
    else:
        sys.exit('# expected for declaration in line ' + str(current_line))


def statements():
    """statements: statement+"""
    global file_name
    global current_line
    statement()
    line = current_line
    pos = file_name.tell()
    lex()
    while family == 'identifier' or token == 'print' or token == 'return' or token == 'if' or token == 'while':
        file_name.seek(pos)
        current_line = line
        statement()
        line = current_line
        pos = file_name.tell()
        lex()
    file_name.seek(pos)
    current_line = line
    return


def statement():
    """statement: simple_statement | structured_statement"""
    global file_name
    global current_line
    line = current_line
    pos = file_name.tell()
    lex()
    if family == 'identifier' or token == 'print' or token == 'return':
        file_name.seek(pos)
        current_line = line
        simple_statement()
    elif token == 'if' or token == 'while':
        file_name.seek(pos)
        current_line = line
        structured_statement()
    else:
        sys.exit('Statement expected in line ' + str(current_line))


def simple_statement():
    """simple_statement: assignment_stat | print_stat | return_stat"""
    global file_name
    global current_line
    line = current_line
    pos = file_name.tell()
    lex()
    if family == 'identifier':
        file_name.seek(pos)
        current_line = line
        assignment_stat()
    elif token == 'print':
        file_name.seek(pos)
        current_line = line
        print_stat()
    elif token == 'return':
        file_name.seek(pos)
        current_line = line
        return_stat()
    else:
        sys.exit('Simple statement expected in line ' + str(current_line))


def structured_statement():
    """structured_statement: if_stat | while_stat"""
    global file_name
    global current_line
    line = current_line
    pos = file_name.tell()
    lex()
    if token == 'if':
        file_name.seek(pos)
        current_line = line
        if_stat()
    elif token == 'while':
        file_name.seek(pos)
        current_line = line
        while_stat()
    else:
        sys.exit('Structured statement expected in line ' + str(current_line))


def assignment_stat():
    """assignment_stat: ID '=' (expression ';' | 'int' '(' 'input' '(' ')' ')' ';')"""
    global file_name
    global current_line
    line = current_line
    lex()
    if family == 'identifier':
        line = current_line
        name = token
        lex()
        if token == '=':
            line = current_line
            pos = file_name.tell()
            lex()
            if token == 'int':
                line = current_line
                lex()
                if token == '(':
                    lex()
                    if token == 'input':
                        gen_quad('inp', name, '_', '_')
                        lex()
                        if token == '(':
                            lex()
                            if token == ')':
                                lex()
                                if token == ')':
                                    lex()
                                    if token == ';':
                                        return
                                    else:
                                        current_line = line
                                        sys.exit('; expected after ) in line ' + str(current_line))
                                else:
                                    sys.exit(') expected after ) in line ' + str(current_line))
                            else:
                                sys.exit(') expected after ( in line ' + str(current_line))
                        else:
                            sys.exit('( expected after "input" in line ' + str(current_line))
                    else:
                        sys.exit('"input" expected after int( in line ' + str(current_line))
                else:
                    sys.exit('( expected after int in line ' + str(current_line))
            else:
                file_name.seek(pos)
                current_line = line
                x = expression()
                gen_quad('=', x, '_', name)
                line = current_line
                lex()
                if token == ';':
                    return
                else:
                    current_line = line
                    sys.exit('; expected after expression in line ' + str(current_line))
        else:
            current_line = line
            sys.exit('= expected after identifier in line ' + str(current_line))
    else:
        current_line = line
        sys.exit('identifier expected in line ' + str(current_line))


def print_stat():
    """print_stat: 'print' '(' expression ')' ';'"""
    global file_name
    global current_line
    lex()
    if token == 'print':
        lex()
        if token == '(':
            x = expression()
            gen_quad('out', x, '_', '_')
            lex()
            if token == ')':
                line = current_line
                lex()
                if token == ';':
                    return
                else:
                    current_line = line
                    sys.exit('; expected after ) in line ' + str(current_line))
            else:
                sys.exit(') expected after expression in line ' + str(current_line))
        else:
            sys.exit('( expected after print in line ' + str(current_line))
    else:
        return


def return_stat():
    """return_stat: 'return' '(' expression ')' ';'"""
    global file_name
    global current_line
    lex()
    if token == 'return':
        lex()
        if token == '(':
            x = expression()
            gen_quad('retv', x, '_', '_')
            lex()
            if token == ')':
                line = current_line
                lex()
                if token == ';':
                    return
                else:
                    current_line = line
                    sys.exit('; expected after ) in line ' + str(current_line))
            else:
                sys.exit(') expected after expression in line ' + str(current_line))
        else:
            sys.exit('( expected after return in line ' + str(current_line))
    else:
        return


def if_stat():
    """if_stat: 'if' '(' condition ')' ':' (statement | '#{' statements '#}') ['else' ':' (statement | '#{' statements '#}')]"""
    global file_name
    global current_line
    lex()
    if token == 'if':
        lex()
        if token == '(':
            [Btrue, Bfalse] = condition()
            lex()
            if token == ')':
                line = current_line
                lex()
                if token == ':':
                    line = current_line
                    pos = file_name.tell()
                    lex()
                    if token == '#{':
                        backpatch(Btrue, next_quad())
                        statements()
                        ifList = makelist(next_quad())
                        gen_quad('jump', '_', '_', '_')
                        backpatch(Bfalse, next_quad())
                        line = current_line
                        lex()
                        if token == '#}':
                            line = current_line
                            pos = file_name.tell()
                            lex()
                            if token == 'else':
                                lex()
                                if token == ':':
                                    line = current_line
                                    pos = file_name.tell()
                                    lex()
                                    if token == '#{':
                                        backpatch(ifList, next_quad())
                                        statements()
                                        lex()
                                        if token == '#}':
                                            return
                                        else:
                                            sys.exit('#} expected after statements in line ' + str(current_line))
                                    else:
                                        file_name.seek(pos)
                                        current_line = line
                                        backpatch(ifList, next_quad())
                                        statement()
                                else:
                                    sys.exit(': expected after else in line ' + str(current_line))
                            else:
                                file_name.seek(pos)
                                current_line = line
                                return
                        else:
                            current_line = line
                            sys.exit('#} expected after statements in line ' + str(current_line))
                    else:
                        file_name.seek(pos)
                        current_line = line
                        backpatch(Btrue, next_quad())
                        statement()
                        ifList = makelist(next_quad())
                        gen_quad('jump', '_', '_', '_')
                        backpatch(Bfalse, next_quad())
                        line = current_line
                        pos = file_name.tell()
                        lex()
                        if token == 'else':
                            line = current_line
                            lex()
                            if token == ':':
                                line = current_line
                                pos = file_name.tell()
                                lex()
                                if token == '#{':
                                    backpatch(ifList, next_quad())
                                    statements()
                                    line = current_line
                                    lex()
                                    if token == '#}':
                                        return
                                    else:
                                        current_line = line
                                        sys.exit('#} expected after statements in line ' + str(current_line))
                                else:
                                    file_name.seek(pos)
                                    current_line = line
                                    backpatch(ifList, next_quad())
                                    statement()
                            else:
                                current_line = line
                                sys.exit(': expected after else in line ' + str(current_line))
                        else:
                            backpatch(ifList, next_quad())
                            file_name.seek(pos)
                            current_line = line
                            return
                else:
                    current_line = line
                    sys.exit(': expected after ) in line ' + str(current_line))
            else:
                sys.exit(') expected after condition in line ' + str(current_line))
        else:
            sys.exit('( expected after if in line ' + str(current_line))
    else:
        return


def while_stat():
    """while_stat: 'while' '(' condition ')' ':' (statement | '#{' statements '#}')"""
    global file_name
    global current_line
    lex()
    if token == 'while':
        lex()
        if token == '(':
            Bquad = next_quad()
            [Btrue, Bfalse] = condition()
            lex()
            if token == ')':
                line = current_line
                lex()
                if token == ':':
                    line = current_line
                    pos = file_name.tell()
                    lex()
                    if token == '#{':
                        backpatch(Btrue, next_quad())
                        statements()
                        gen_quad('jump', '_', '_', Bquad)
                        backpatch(Bfalse, next_quad())
                        line = current_line
                        lex()
                        if token == '#}':
                            return
                        else:
                            current_line = line
                            sys.exit('#} expected after statements in line ' + str(current_line))
                    else:
                        file_name.seek(pos)
                        current_line = line
                        backpatch(Btrue, next_quad())
                        statement()
                        gen_quad('jump', '_', '_', Bquad)
                        backpatch(Bfalse, next_quad())
                else:
                    current_line = line
                    sys.exit(': expected after ) in line ' + str(current_line))
            else:
                sys.exit(') expected after condition in line ' + str(current_line))
        else:
            sys.exit('( expected after while in line ' + str(current_line))
    else:
        return


def id_list():
    """id_list: ID (',' ID)*   Adds each ID to the current scope."""
    global file_name
    global current_line
    global depth
    line = current_line
    lex()
    if family == 'identifier':
        # Formal parameters and declared variables are both stored as Parameter entities.
        myScope[depth].addEntity(Parameter(token, 'Integer', myScope[depth].nextOffset()))
        line = current_line
        pos = file_name.tell()
        lex()
        if token == ',':
            id_list()
        else:
            file_name.seek(pos)
            current_line = line
            return
    else:
        current_line = line
        sys.exit('identifier expected in line ' + str(current_line))


def expression():
    """expression: optional_sign term (ADD_OP term)*   Returns the name that holds the result."""
    global file_name
    global current_line
    op_s = optional_sign()
    x = op_s + term()
    line = current_line
    pos = file_name.tell()
    lex()
    while family == 'addOperator':
        op = token
        y = term()
        z = newtemp()
        gen_quad(op, x, y, z)
        x = z
        line = current_line
        pos = file_name.tell()
        lex()
    file_name.seek(pos)
    current_line = line
    return x


def term():
    """term: factor (MUL_OP factor)*   Returns the name that holds the result."""
    global file_name
    global current_line
    x = factor()
    line = current_line
    pos = file_name.tell()
    lex()
    while family == 'mulOperator':
        op = token
        y = factor()
        z = newtemp()
        gen_quad(op, x, y, z)
        x = z
        line = current_line
        pos = file_name.tell()
        lex()
    file_name.seek(pos)
    current_line = line
    return x


def factor():
    """factor: INTEGER | '(' expression ')' | ID idtail   Returns the name that holds the result."""
    global file_name
    global current_line
    lex()
    value = token
    if family == 'number':
        return value
    elif token == '(':
        value = expression()
        lex()
        if token == ')':
            return value
        else:
            sys.exit(') expected after expression in line ' + str(current_line))
    elif family == 'identifier':
        if idtail():
            x = newtemp()
            gen_quad('par', x, 'ret', '_')
            gen_quad('call', value, '_', '_')
            value = x
    else:
        sys.exit('Factor expected in line ' + str(current_line))
    return value


def idtail() -> bool:
    """idtail: '(' actual_par_list ')' | empty   Returns True if it was a function call."""
    global file_name
    global current_line
    line = current_line
    pos = file_name.tell()
    lex()
    if token == '(':
        actual_par_list()
        lex()
        if token == ')':
            return True
        else:
            sys.exit(') expected after parameters in line ' + str(current_line))
    else:
        file_name.seek(pos)
        current_line = line
        return False


def actual_par_list():
    """actual_par_list: expression (',' expression)* | empty"""
    global file_name
    global current_line
    line = current_line
    pos = file_name.tell()
    lex()
    if token == ')':
        file_name.seek(pos)
        current_line = line
        return
    file_name.seek(pos)
    current_line = line
    x = expression()
    gen_quad('par', x, 'CV', '_')
    line = current_line
    pos = file_name.tell()
    lex()
    while token == ',':
        x = expression()
        gen_quad('par', x, 'CV', '_')
        line = current_line
        pos = file_name.tell()
        lex()
    file_name.seek(pos)
    current_line = line
    return


def optional_sign():
    """optional_sign: ADD_OP | empty   Returns the sign, or ''."""
    global file_name
    global current_line
    line = current_line
    pos = file_name.tell()
    lex()
    sign = token
    if family == 'addOperator':
        return sign
    else:
        file_name.seek(pos)
        current_line = line
        return ''


def condition():
    """condition: bool_term ('or' bool_term)*   Returns the [true, false] lists of jumps to backpatch."""
    global file_name
    global current_line
    [Q1true, Q1false] = bool_term()
    line = current_line
    pos = file_name.tell()
    lex()
    Btrue = Q1true
    Bfalse = Q1false
    while token == 'or':
        # If the left side is false, evaluation continues with the next bool_term.
        backpatch(Bfalse, next_quad())
        line = current_line
        pos = file_name.tell()
        lex()
        [Q2true, Q2false] = bool_term()
        Btrue = merge(Btrue, Q2true)
        Bfalse = Q2false
    file_name.seek(pos)
    current_line = line
    return [Btrue, Bfalse]


def bool_term():
    """bool_term: bool_factor ('and' bool_factor)*   Returns the [true, false] lists."""
    global file_name
    global current_line
    [R1true, R1false] = bool_factor()
    Qtrue = R1true
    Qfalse = R1false
    line = current_line
    pos = file_name.tell()
    lex()
    while token == 'and':
        # If the left side is true, evaluation continues with the next bool_factor.
        backpatch(Qtrue, next_quad())
        [R2true, R2false] = bool_factor()
        Qfalse = merge(Qfalse, R2false)
        Qtrue = R2true
        line = current_line
        pos = file_name.tell()
        lex()
    file_name.seek(pos)
    current_line = line
    return [Qtrue, Qfalse]


def bool_factor():
    """bool_factor: 'not' '[' condition ']' | '[' condition ']' | expression REL_OP expression"""
    global file_name
    global current_line
    line = current_line
    pos = file_name.tell()
    lex()
    if token == 'not':
        lex()
        if token == '[':
            [Btrue, Bfalse] = condition()
            lex()
            if token == ']':
                # not: swap the true and false lists
                Rtrue = Bfalse
                Rfalse = Btrue
            else:
                sys.exit('] expected after condition in line ' + str(current_line))
        else:
            sys.exit('[ expected after not in line ' + str(current_line))
    elif token == '[':
        [Btrue, Bfalse] = condition()
        lex()
        if token == ']':
            Rtrue = Btrue
            Rfalse = Bfalse
        else:
            sys.exit('] expected after condition in line ' + str(current_line))
    else:
        file_name.seek(pos)
        current_line = line
        x = expression()
        lex()
        if family == 'relOperator':
            op = token
            y = expression()
            # A conditional jump for "true" and a plain jump for "false". Their
            # targets are unknown yet and are filled in later by backpatch().
            Rtrue = makelist(next_quad())
            gen_quad(op, x, y, '_')
            Rfalse = makelist(next_quad())
            gen_quad('jump', '_', '_', '_')
        else:
            sys.exit('Relational operator expected after expression in line ' + str(current_line))
    return [Rtrue, Rfalse]


def call_main_part():
    """call_main_part: 'if' '__name__' '==' '"__main__"' ':' main_function_call+"""
    global file_name
    global current_line
    lex()
    if token == 'if':
        lex()
        if token == '__name__':
            lex()
            if token == '==':
                lex()
                if token == '"__main__"':
                    line = current_line
                    lex()
                    if token == ':':
                        main_function_call()
                        line = current_line
                        pos = file_name.tell()
                        lex()
                        while family == 'identifier':
                            file_name.seek(pos)
                            current_line = line
                            main_function_call()
                            pos = file_name.tell()
                            line = current_line
                            lex()
                        file_name.seek(pos)
                        current_line = line
                        return
                    else:
                        current_line = line
                        sys.exit(': expected after "__main__" in line ' + str(current_line))
                else:
                    sys.exit('"__main__" expected after == in line ' + str(current_line))
            else:
                sys.exit('== expected after __name__ in line ' + str(current_line))
        else:
            sys.exit('__name__ expected after if in line ' + str(current_line))
    else:
        sys.exit('if expected in line ' + str(current_line))


def main_function_call():
    """main_function_call: ID '(' ')' ';'"""
    global file_name
    global current_line
    lex()
    if family == 'identifier':
        lex()
        if token == '(':
            lex()
            if token == ')':
                line = current_line
                lex()
                if token == ';':
                    return
                else:
                    current_line = line
                    sys.exit('; expected after ) in line ' + str(current_line))
            else:
                sys.exit(') expected after ( in line ' + str(current_line))
        else:
            sys.exit('( expected after identifier in line ' + str(current_line))
    else:
        sys.exit('Identifier for main function call expected in line ' + str(current_line))


#####################################
#               Lexer               #
#####################################

def lex():
    """Read the next token into the globals token and family (token is '' at end of file)."""
    global file_name
    global current_line
    global token
    global position
    global family
    token = ''
    family = ''
    position = file_name.tell()
    char = file_name.read(1)

    # End of file (or empty file): return an empty token
    if char == '':
        print('Syntax and lex completed without errors.')
        return

    # Skip whitespace, counting lines
    while char == ' ' or char == '\n' or char == '\t':
        if char == '\n':
            current_line += 1
        position = file_name.tell()
        char = file_name.read(1)

    # Integer constant (must be followed by an operator, delimiter or whitespace)
    while char.isdigit():
        token += char
        position = file_name.tell()
        char = file_name.read(1)
        if char.isalpha() or char == '_':
            sys.exit('No letter or underscore expected in line: ' + str(current_line))
        elif not legal_character(char):
            sys.exit('Unexpected character following ' + token + ' in line: ' + str(current_line))
        elif char.isdigit():
            position = file_name.tell()
        else:
            file_name.seek(position)
            if -(2 ** 32) >= int(token) or int(token) >= 2 ** 32:
                sys.exit('Number ' + token + ' out of range in line ' + str(current_line))
            family = 'number'
            return

    # Identifier or keyword
    if char.isalpha():
        token = char
        position = file_name.tell()
        char = file_name.read(1)
        while char.isalnum() or char == '_':
            token += char
            position = file_name.tell()
            char = file_name.read(1)
        file_name.seek(position)
        if len(token) > 30:
            sys.exit('String ' + token + ' too long in line ' + str(current_line))
        if token not in keywords:
            family = 'identifier'
        else:
            family = 'keyword'
        return

    # Single-character operators
    if char == '+' or char == '-' or char == '*':
        token = char
        if token == '*':
            family = 'mulOperator'
        else:
            family = 'addOperator'
        return

    # Integer division //
    if char == '/':
        token += char
        char = file_name.read(1)
        if char != '/':
            sys.exit('/ expected after / in line: ' + str(current_line))
        token += char
        family = 'mulOperator'
        return

    # Relational operators and assignment
    if char == '<':
        token += char
        position = file_name.tell()
        char = file_name.read(1)
        if char == '=':
            token += char
            family = 'relOperator'
            return
        file_name.seek(position)
        family = 'relOperator'
        return

    if char == '>':
        token += char
        position = file_name.tell()
        char = file_name.read(1)
        if char == '=':
            token += char
            family = 'relOperator'
            return
        file_name.seek(position)
        family = 'relOperator'
        return

    if char == '!':
        token += char
        char = file_name.read(1)
        if char != '=':
            sys.exit('= expected after ! in line: ' + str(current_line))
        token += char
        family = 'relOperator'
        return

    if char == '=':
        token += char
        position = file_name.tell()
        char = file_name.read(1)
        if char == '=':
            token += char
            family = 'relOperator'
            return
        file_name.seek(position)
        family = 'assignment'
        return

    # Delimiters
    if char == ';' or char == ',' or char == ':':
        token = char
        if token == ';':
            family = 'semicolon'
        elif token == ',':
            family = 'comma'
        else:
            family = 'colon'
        return

    # Grouping symbols, #{ and #} blocks, and #$ ... #$ comments (skipped)
    if char == '[' or char == ']' or char == '(' or char == ')':
        token = char
        return
    elif char == '#':
        token += char
        position = file_name.tell()
        char = file_name.read(1)
        if char == '{':
            token += char
            return
        elif char == '}':
            token += char
            return
        elif char == '$':
            char = file_name.read(1)
            while char != '#':
                if char == '\n':
                    current_line += 1
                char = file_name.read(1)
            char = file_name.read(1)
            if char == '$':
                token = ''
                lex()
                return
        else:
            file_name.seek(position)
    if not legal_character(char):
        sys.exit('Illegal character ' + char + ' in line: ' + str(current_line))

    # __name__ (used only in the call section)
    if char == '_':
        token += char
        char = file_name.read(1)
        if char == '_':
            token += char
            char = file_name.read(1)
            if char == 'n':
                token += char
                char = file_name.read(1)
                if char == 'a':
                    token += char
                    char = file_name.read(1)
                    if char == 'm':
                        token += char
                        char = file_name.read(1)
                        if char == 'e':
                            token += char
                            char = file_name.read(1)
                            if char == '_':
                                token += char
                                char = file_name.read(1)
                                if char == '_':
                                    token += char
                                    return
                                else:
                                    sys.exit('Illegal word starting with _ in line ' + str(current_line))
                            else:
                                sys.exit('Illegal word starting with _ in line ' + str(current_line))
                        else:
                            sys.exit('Illegal word starting with _ in line ' + str(current_line))
                    else:
                        sys.exit('Illegal word starting with _ in line ' + str(current_line))
                else:
                    sys.exit('Illegal word starting with _ in line ' + str(current_line))
            else:
                sys.exit('Illegal word starting with _ in line ' + str(current_line))
        else:
            sys.exit('Illegal word starting with _ in line ' + str(current_line))

    # "__main__" (used only in the call section)
    if char == '"':
        token += char
        char = file_name.read(1)
        if char == '_':
            token += char
            char = file_name.read(1)
            if char == '_':
                token += char
                char = file_name.read(1)
                if char == 'm':
                    token += char
                    char = file_name.read(1)
                    if char == 'a':
                        token += char
                        char = file_name.read(1)
                        if char == 'i':
                            token += char
                            char = file_name.read(1)
                            if char == 'n':
                                token += char
                                char = file_name.read(1)
                                if char == '_':
                                    token += char
                                    char = file_name.read(1)
                                    if char == '_':
                                        token += char
                                        char = file_name.read(1)
                                        if char == '"':
                                            token += char
                                            return
                                        else:
                                            sys.exit('Illegal word starting with " in line ' + str(current_line))
                                    else:
                                        sys.exit('Illegal word starting with " in line ' + str(current_line))
                                else:
                                    sys.exit('Illegal word starting with " in line ' + str(current_line))
                            else:
                                sys.exit('Illegal word starting with " in line ' + str(current_line))
                        else:
                            sys.exit('Illegal word starting with " in line ' + str(current_line))
                    else:
                        sys.exit('Illegal word starting with " in line ' + str(current_line))
                else:
                    sys.exit('Illegal word starting with " in line ' + str(current_line))
            else:
                sys.exit('Illegal word starting with " in line ' + str(current_line))
        else:
            sys.exit('Illegal word starting with " in line ' + str(current_line))
    return


def legal_character(character) -> bool:
    """Return True if the character may appear in a CutePy program."""
    if character.isalnum() or character in legal_symbols:
        return True
    return False


main()
