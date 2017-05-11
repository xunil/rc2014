;==================================================================================================
;   FLOPPY DISK DRIVER - DATA
;==================================================================================================

DIOBUF          .DW      0
HSTDSK          .DB      0
HSTTRK          .DW      0
HSTSEC          .DW      0

;
; FDC COMMAND PHASE
;
FCP_CMD		.DB	000H
FCP_LEN		.DB	00H
FCP_BUF:
FCP_CMDX	.DB	0
FCP_HDSDS	.DB	0
FCP_C		.DB	0
FCP_H		.DB	0
FCP_R		.DB	0
FCP_N		.DB	0
FCP_EOT		.DB	0
FCP_GPL		.DB	0
FCP_DTL		.DB	0
FCP_BUFSIZ	.EQU	$-FCP_BUF
;
; FDC STATUS
;
FST_RC		.DB	00H
FST_DOR		.DB	00H
FST_DCR		.DB	00H
;
; FDC RESULTS BUFFER
;
FRB_LEN		.DB	00H
FRB
FRB_ST0
FRB_ST3		.DB	0
FRB_ST1
FRB_PCN		.DB	0
FRB_ST2		.DB	0
FRB_C		.DB	0
FRB_H		.DB	0
FRB_R		.DB	0
FRB_N		.DB	0
FRB_SIZ		.EQU	$-FRB
;
; FDC COMMAND DATA
;
FCD:		; FLOPPY CONFIGURATION DATA (PUBLIC) MANAGED AS A "BLOCK"
FCD_NUMCYL	.DB	000H		; NUMBER OF CYLINDERS
FCD_NUMHD	.DB	000H		; NUMBER OF HEADS
FCD_NUMSEC	.DB	000H		; NUMBER OF SECTORS
FCD_SOT		.DB	000H		; START OF TRACK (ID OF FIRST SECTOR, USUALLY 1)
FCD_EOT					; END OF TRACK SECTOR (SAME AS SC SINCE SOT ALWAYS 1)
FCD_SC		.DB	000H		; SECTOR COUNT
FCD_SECSZ	.DW	000H		; SECTOR SIZE IN BYTES
FCD_GPL		.DB	000H		; GAP LENGTH (R/W)
FCD_GPLF	.DB	000H		; GAP LENGTH (FORMAT)
FCD_SRTHUT	.DB	000H		; STEP RATE, IBM PS/2 CALLS FOR 3ms, 0DH = 3ms SRT, HEAD UNLOAD TIME
FCD_HLTND	.DB	000H		; HEAD LOAD TIME, IBM PS/2 CALLS FOR 15ms 08H = 16ms HUT
FCD_DOR		.DB	000H		; DOR VALUE
FCD_DCR		.DB	000H		; DCR VALUE
FCD_LEN		.EQU	$ - FCD
		; DYNAMICALLY MANAGED (PUBLIC)
FCD_DS		.DB	001H		; DRIVE SELECT (UNIT NUMBER 0-3)
FCD_C		.DB	000H		; CYLINDER
FCD_H		.DB	000H		; HEAD
FCD_R		.DB	001H		; RECORD
FCD_D		.DB	0E5H		; DATA FILL BYTE
		; STATUS MANAGEMENT
FCD_DOP		.DB	0FFH		; CURRENT OPERATION (SEE DOP_...)
FCD_IDLECNT	.DW	0		; IDLE COUNT
FCD_TRACE	.DB	0		; TRACE LEVEL
FCD_TO		.DB	0		; TIMEOUT COUNTDOWN TIMER
FCD_FDCRDY	.DB	0		; FALSE MEANS FDC RESET NEEDED
;
; FLOPPY UNIT DATA
;
FCD_UNITS:
FCD_U0TRK	.DB	0FFH		; CURRENT TRACK
FCD_U0MEDIA	.DB	FDMEDIA		; MEDIA BYTE
;		.DW	FDDPH0		; ADDRESS OF DPH
;
FCD_U1TRK	.DB	0FFH		; CURRENT TRACK
FCD_U1MEDIA	.DB	FDMEDIA		; MEDIA BYTE
;
; WORKING STORAGE (DERIVED FROM ABOVE FOR ACTIVE DRIVE UNIT)
;
FDDS_TRKADR	.DW	0	; POINTER TO FDCUXTRK ABOVE
FDDS_MEDIAADR	.DW	0	; POINTER TO FDCUXMEDIA ABOVE

