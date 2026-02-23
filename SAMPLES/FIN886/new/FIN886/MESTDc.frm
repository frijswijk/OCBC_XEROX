%!
%%Title: MESTDc.frm
%%Creator: Lian
%%CreationDate: Fri Feb 22 2020, 22:22:22.
%%EndComments

{  %%Begin Form

    MM SETUNIT
    ORITL
    PORT
    2 SETLSP

    % Define Font Indexing
    % ------------------------------------------------
    (~~) 2 SETFTSW

    /F1  /ARIALB	05  INDEXFONT
    /F2  /ARIAL		06  INDEXFONT
    /F3	 /ARIALB	06  INDEXFONT
    /F4	 /ARIALO	06  INDEXFONT
    /F5	 /ARIALBO	06  INDEXFONT
    /F6	 /ARIAL		07  INDEXFONT
    /F7  /ARIALB	07  INDEXFONT
    /F8  /ARIALO	07  INDEXFONT
    /F9  /ARIALBO	07  INDEXFONT
    /F0  /ARIAL		08  INDEXFONT
    /FA  /ARIALB	08  INDEXFONT
    /FB	 /ARIALO	08  INDEXFONT
    /FC	 /ARIALBO	08  INDEXFONT
    /FD  /ARIALB	09  INDEXFONT
    /FE	 /ARIAL		10  INDEXFONT
    /FF	 /NHEB	 	07	INDEXFONT
    /FG  /NHEBO 	07 	INDEXFONT
    /FH  /NHE 	 	07 	INDEXFONT

    % Define Colour Indexing
    % ------------------------------------------------
    /B    	BLACK          	  INDEXCOLOR
    /W    	WHITE          	  INDEXCOLOR
    /R    	RED            	  INDEXCOLOR

    % Define BatKey Indexing
    % ------------------------------------------------
    /U0 	/UNDL 			  INDEXBAT
    /N0 	 null 			  INDEXBAT

    % Define Interative features for URL
    % -----------------------------------
    /L0 [ /URI ] INDEXPIF
    /L1 null 	 INDEXPIF

    % Define Dynamic Elements
    % ------------------------------------------------
    /TXNB  {  0   0    188    09  LMED     DRAWB} XGFRESDEF

    % June 2023
    10.7 16.2 MOVETO (OCBC.eps) CACHE 0.38  SCALL

    131.3 04  MOVETO F7 (OCBC Bank (Malaysia) Berhad 199401009721 (295400-W)) SHL

    % June 2023
    03 SETLSP
    131.3 11 MOVETO  F6  (Personal Banking Enquiries  03-8317 5000                         )    SHL
    (Business Banking Enquiries 1300-88-7000 / 03-8317 5200)    SHL

    % Draw a horizontal line
    12 17 187 0.2 R_S1 DRAWB

    %FC

    118 33 35 06 XLTR DRAWB

    120 37 MOVETO FA (MERCHANT NUMBER) SHL

    118 40 35 06 XLTR DRAWB

    120 44 MOVETO FA (STATEMENT DATE) SHL

    188.1 22.6 MOVETO F2 (PAGE) SHL

    % Insert URL text
    F2
    1.5 SETLSP
    B

    % Insert Group Name
    F2
    B
    199 290 MOVETO
    (A Member of OCBC Group) SHR

    R
    NL
    (https://www.ocbc.com.my) SHR
    B

} FSHOW
