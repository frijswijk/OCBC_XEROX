%!
%%Title: CASIOS.FRM
%%Creator: Lian
%%CreationDate: Mon Oct 23 2011, 14:28:30.
%%EndComments

{  %%Begin Form

    MM SETUNIT
    ORITL
    PORT
    02 SETLSP

    % Define Font Indexing
    % ------------------------------------------------
    (**) 2 SETFTSW
    /F1  	/ARIALB   	07    INDEXFONT
    /F2  	/ARIAL    	06    INDEXFONT
    /F3  	/ARIAL    	08    INDEXFONT
    /F4  	/ARIALB   	09    INDEXFONT
    /F5  	/ARIALBO  	07    INDEXFONT
    /F6  	/ARIAL    	07    INDEXFONT
    /F7  	/ARIALBO  	08    INDEXFONT
    /F8  	/ARIAL      10    INDEXFONT
    /F0		/ARIALO	    08    INDEXFONT
    /FA		/ARIALB	    10    INDEXFONT
    /FB		/ARIALB     08    INDEXFONT
    /FC     /ARIALO     07    INDEXFONT
    /FD     /ARIALB    6.5    INDEXFONT
    /FE     /ARIAL     6.5    INDEXFONT
    /FF     /ARIALBO   6.5    INDEXFONT
    /FG     /ARIALO    6.5    INDEXFONT
    /FH     /ARIALB     12	  INDEXFONT
    /FI     /ARIALB     13    INDEXFONT

    % Define Colour Indexing
    /B    	BLACK          	  INDEXCOLOR
    /W    	WHITE          	  INDEXCOLOR
    /R    	RED            	  INDEXCOLOR

    % Define BatKey Indexing
    /U0 	/UNDL 			  INDEXBAT
    /N0 	 null 			  INDEXBAT

    % Define Color Indexing
    % ------------------------------------------------
    /B    BLACK       INDEXCOLOR
    /R    RED         INDEXCOLOR

    % ------------------------------------------------
    % Year End Summary Box - prefix for YR
    /YRSB	{	% 00   -14    173     08     FBLACK     DRAWB % Shaded Box
        % 20210427
        00   -14    193     08     FBLACK     DRAWB % Shaded Box

    } XGFRESDEF		% Year End Summary
    % ------------------------------------------------

    %June 2023
    10 16 MOVETO (OCBC.eps) CACHE 0.38  SCALL
    131.3 04  MOVETO F1 (OCBC Bank (Malaysia) Berhad 199401009721 (295400-W)) SHL

    %June 2023
    12 17 187 0.2 R_S1 DRAWB

    % June 2023
    03 SETLSP
    131.3 11 MOVETO  F6  (Personal Banking Enquiries  03-8317 5000                         )    SHL
    (Business Banking Enquiries 1300-88-7000 / 03-8317 5200)    SHL

    % 20210427
    08 50 MOVETO
    (YRSB)SCALL

    % 20210427
    12 69.5 MOVETO
    W FH (Summary of Account Activity for) SH
    B

    % Insert Customer Variables
    % ------------------------------------------------
    F8
    18.5 25 MOVETO
    W
    (Account - )SH
    VAR_ARRAY1F1 (#### #### #### ####) FORMAT SH
    B
    18.5 30 MOVETO
    05 SETLSP
    VAR_CN1  90  0  SHP
    VAR_AD1  90  0  SHP
    VAR_AD2  90  0  SHP
    VAR_AD3  90  0  SHP
    VAR_AD4  90  0  SHP
    VAR_AD5  90  0  SHP
    VAR_PCS  90  0  SHP

    % 2011-09-26
    10 283 MOVETO

    % Insert URL text
    % ------------------------------------------------
    F6 B
    03 SETLSP
    128 290 MOVETO
    01 NL

    % Insert Group Name
    % ------------------------------------------------
    F6  B  186.5 290 MOVETO  (A Member of OCBC Group) SHC

    R  (https://www.ocbc.com.my) SHC  B
    01 NL

    % 20210427

} % FSHOW

%%EOF
