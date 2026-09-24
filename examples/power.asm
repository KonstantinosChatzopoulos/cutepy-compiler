Lpower:
	sw ra, (sp)
L1:
	lw t1, -16(sp)
	li t2, 0
	beq t1, t2, L3
L2:
	j L5
L3:
	li t1, 1
	lw t0, -8(sp)
	sw t1, (t0)
L4:
	j L5
L5:
	addi fp, sp, 20
	lw t0, -12(sp)
	sw t0, -12(fp)
L6:
	lw t1, -16(sp)
	li t2, 1
	sub t1, t1, t2
	sw t1, -20(sp)
L7:
	lw t0, -20(sp)
	sw t0, -16(fp)
L8:
	addi t0, sp, -24
	sw t0, -8(fp)
L9:
	sw sp, -4(fp)
	addi sp, sp,32
	jal Lpower
	addi sp, sp, -32
L10:
	lw t1, -12(sp)
	lw t2, -24(sp)
	mul t1, t1, t2
	sw t1, -28(sp)
L11:
	lw t1, -28(sp)
	lw t0, -8(sp)
	sw t1, (t0)
L12:
Lmain_power:
	sw ra, (sp)
L14:
	li a7, 5
	ecall
L15:
	li a7, 5
	ecall
L16:
	addi fp, sp, 20
	lw t0, -12(s0)
	sw t0, -12(fp)
L17:
	lw t0, -16(s0)
	sw t0, -16(fp)
L18:
	addi t0, sp, -24
	sw t0, -8(fp)
L19:
	lw t0, -4(sp)
	sw t0, -4(fp)
	addi sp, sp,28
	jal Lpower
	addi sp, sp, -28
L20:
	lw a0, -24(gp)
	li a7, 1
	ecall
L21:
	li a0, 10
	ecall
L22:
