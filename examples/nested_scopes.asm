Lstep:
	sw ra, (sp)
L1:
	lw t1, -12(sp)
	lw t2, -12(s0)
	ble t1, t2, L3
L2:
	j L7
L3:
	lw t1, -12(sp)
	li t2, 0
	beq t1, t2, L7
L4:
	j L5
L5:
	lw t1, -12(sp)
	lw t0, -8(sp)
	sw t1, (t0)
L6:
	j L7
L7:
	li t1, 0
	lw t0, -8(sp)
	sw t1, (t0)
L8:
LsumTo:
	sw ra, (sp)
L10:
	li t1, 0
	lw t0, -4(sp)
	addi t0, t0, -20
	sw t1, (t0)
L11:
	li t1, 1
	lw t0, -4(sp)
	addi t0, t0, -16
	sw t1, (t0)
L12:
	lw t0, -4(sp)
	addi t0, t0, -16
	lw t1, (t0)
	lw t0, -4(sp)
	addi t0, t0, -12
	lw t2, (t0)
	ble t1, t2, L14
L13:
	j L22
L14:
	addi fp, sp, 24
	lw t0, -4(sp)
	addi t0, t0, -16
	lw t0, (t0)
	sw t0, -12(fp)
L15:
	addi t0, sp, -28
	sw t0, -8(fp)
L16:
	lw t0, -4(sp)
	sw t0, -4(fp)
	addi sp, sp,40
	jal Lstep
	addi sp, sp, -40
L17:
	lw t0, -4(sp)
	addi t0, t0, -20
	lw t1, (t0)
	lw t0, -4(sp)
	addi t0, t0, -28
	lw t2, (t0)
	add t1, t1, t2
	lw t0, -4(sp)
	addi t0, t0, -32
	sw t1, (t0)
L18:
	lw t0, -4(sp)
	addi t0, t0, -32
	lw t1, (t0)
	lw t0, -4(sp)
	addi t0, t0, -20
	sw t1, (t0)
L19:
	lw t0, -4(sp)
	addi t0, t0, -16
	lw t1, (t0)
	li t2, 1
	add t1, t1, t2
	lw t0, -4(sp)
	addi t0, t0, -36
	sw t1, (t0)
L20:
	lw t0, -4(sp)
	addi t0, t0, -36
	lw t1, (t0)
	lw t0, -4(sp)
	addi t0, t0, -16
	sw t1, (t0)
L21:
	j L12
L22:
	lw t0, -4(sp)
	addi t0, t0, -20
	lw t1, (t0)
	lw t0, -8(sp)
	sw t1, (t0)
L23:
Lmain_nested:
	sw ra, (sp)
L25:
	li t1, 5
	sw t1, -12(s0)
L26:
	addi fp, sp, 20
	li t0, 10
	sw t0, -12(fp)
L27:
	addi t0, sp, -24
	sw t0, -8(fp)
L28:
	lw t0, -4(sp)
	sw t0, -4(fp)
	addi sp, sp,28
	jal LsumTo
	addi sp, sp, -28
L29:
	lw t1, -24(s0)
	sw t1, -16(s0)
L30:
	lw a0, -16(gp)
	li a7, 1
	ecall
L31:
	li a0, 10
	ecall
L32:
