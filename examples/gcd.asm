Lmain_gcd:
	sw ra, (sp)
L1:
	li a7, 5
	ecall
L2:
	li a7, 5
	ecall
L3:
	lw t1, -16(s0)
	li t2, 0
	bne t1, t2, L5
L4:
	j L12
L5:
	lw t1, -12(s0)
	lw t2, -16(s0)
	div t1, t1, t2
	sw t1, -24(s0)
L6:
	lw t1, -24(s0)
	lw t2, -16(s0)
	mul t1, t1, t2
	sw t1, -28(s0)
L7:
	lw t1, -12(s0)
	lw t2, -28(s0)
	sub t1, t1, t2
	sw t1, -32(s0)
L8:
	lw t1, -32(s0)
	sw t1, -20(s0)
L9:
	lw t1, -16(s0)
	sw t1, -12(s0)
L10:
	lw t1, -20(s0)
	sw t1, -16(s0)
L11:
	j L3
L12:
	lw a0, -12(gp)
	li a7, 1
	ecall
L13:
	li a0, 10
	ecall
L14:
