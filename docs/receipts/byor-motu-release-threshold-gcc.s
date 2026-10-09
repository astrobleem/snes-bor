	.file	"gcc_expression.c"
	.text
	.p2align 4
	.globl	_probe
	.def	_probe;	.scl	2;	.type	32;	.endef
_probe:
	subl	$20, %esp
	movl	_self, %eax
	flds	LC0
	movl	4(%eax), %edx
	movd	(%eax), %xmm0
	movl	4(%eax,%edx,4), %edx
	movl	_animattacks-4(,%edx,4), %edx
	movl	12(%eax,%edx,4), %edx
	xorl	%eax, %eax
	fmuls	(%edx)
	movq	%xmm0, 8(%esp)
	fildq	8(%esp)
	movd	_time, %xmm0
	faddp	%st, %st(1)
	movq	%xmm0, (%esp)
	fildq	(%esp)
	fcomip	%st(1), %st
	fstp	%st(0)
	seta	%al
	addl	$20, %esp
	ret
	.globl	_time
	.bss
	.align 4
_time:
	.space 4
	.globl	_animattacks
	.align 4
_animattacks:
	.space 4
	.globl	_self
	.data
	.align 4
_self:
	.long	_e
	.globl	_e
	.bss
	.align 4
_e:
	.space 16
	.globl	_anim
	.align 4
_anim:
	.space 4
	.section .rdata,"dr"
	.align 4
LC0:
	.long	1128792064
	.ident	"GCC: (Rev13, Built by MSYS2 project) 15.2.0"
