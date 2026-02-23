%!
%%Title: UT00060.frm
%%Creator: Lian
%%CreationDate: Wed Jan 23 2019, 10:28:44.
%%EndComments

{  %%Begin Form

    MM SETUNIT
    ORITL
    PORT
    04 SETLSP

    % Define Font Indexing
    % ------------------------------------------------
    (**) 2 SETFTSW

    /F1   /Helvetica-Bold   07  INDEXFONT
    /F2   /Helvetica    	06  INDEXFONT
    /F3   /Helvetica    	08  INDEXFONT
    /F4   /Helvetica-Bold   09  INDEXFONT
    /F5   /Helvetica-Bold  	07  INDEXFONT
    /F6	  /Helvetica-Bold  	06  INDEXFONT
    /F7   /Helvetica-Bold   08  INDEXFONT
    /F8   /Helvetica-Bold   06  INDEXFONT
    /F9   /Helvetica    	10  INDEXFONT
    /F10  /Helvetica-Bold   10  INDEXFONT
    /F11  /Helvetica-Bold   18  INDEXFONT
    /F12  /Helvetica    	11  INDEXFONT
    /FA   /Helvetica-Bold   12  INDEXFONT

    % Define Colour Indexing
    % ------------------------------------------------

    /B0    	BLACK          	  INDEXCOLOR
    /W0    	WHITE          	  INDEXCOLOR
    /R0    	RED            	  INDEXCOLOR

    % Define BatKey Indexing
    % ------------------------------------------------
    /S0  /SUP  INDEXSST
    /N0  null  INDEXSST
    /U0  /UNDL INDEXBAT
    /N1  null  INDEXBAT

    % insert private and confidential
    F4
    12 31 MOVETO
    (Private & Confidential) SH

    % June 2023
    131.3 20 68 0.1 FBLACK DRAWB

    % insert phone logo
    135 25 MOVETO
    (mobile.jpg) 0.17 0 ICALL

    % insert personal banking enquiries
    F10
    142.5 28 MOVETO
    (Personal Banking Enquiries) SHL

    F9
    01 NL
    (03-8317 5000) SHL

    F10
    NL
    (Business Banking Enquiries) SHL

    F9
    01 NL
    (1300-88-7000 / 03-8317 5200) SHL

    % June 2023
    131.3 90 68 0.1 FBLACK DRAWB

    % insert right column paragraph
    137 99 MOVETO F9 (Your transaction is registered under: Malaysia Nominess (Tempatan) Sdn. Bhd. (6193-K)) 65 0 SHP

    % insert header
    F11
    07 SETLSP
    12 76 MOVETO

    CASE VAR_TRT {()}% default

    (subscription)                     {(Here are the details of your unit trust purchase) 113 0 SHP}
    (monthly investment plan)      	   {(Here are the details of your unit trust monthly investment plan) 113 0 SHP}
    (redemption)                	   {(Here are the details of the unit trust you have sold) 113 0 SHP}
    (internal unit trust transfer) 	   {(Here are the details of your internal unit trust transfer) 113 0 SHP}
    (external unit trust transfer)     {(Here are the details of your external unit trust transfer) 113 0 SHP}

ENDCASE

    % insert dear valued customer
    12 90 113 0.1 FBLACK DRAWB

    %-----------------------
    IF VAR_TRT (subscription) eq  {

        % insert footer
        04 SETLSP
        F3 12 253 MOVETO (Please note:) SHL
        01 NL
        [ [ /Width 05  /FixHeight 07 /Margins  [0 0 0 0] /TextAtt {F3} /CellText (1.)  /Align 0 ]
        [ /Width 180 /FixHeight 07 /Margins  [0 0 0 0] /TextAtt {F3} /CellText (This is a computer generated transaction confirmation, therefore carries no signature. The validity of this confirmation is subject to the clearance of your cheque(s), if applicable.) /Align 0 ]
        ] SHROW

        01 NL
        [ [ /Width 05  /FixHeight 07 /Margins  [0 0 0 0] /TextAtt {F3} /CellText (2.) VSUB4 /Align 000020 ]						% tenure
        [ /Width 180 /FixHeight 07 /Margins  [0 0 0 0] /TextAtt {F3} /CellText (The items and figures shown above is considered correct unless we receive a written notification of any discrepancy within 7 business days from the date this confirmation is issued.) /Align 0 ]
        ] SHROW	 } ENDIF

    %---------------------------------
    IF VAR_TRT (monthly investment plan) eq  {

        % insert footer
        04 SETLSP
        F3 12 253 MOVETO (Please note:) SHL
        01 NL
        [ [ /Width 05  /FixHeight 07 /Margins  [0 0 0 0] /TextAtt {F3} /CellText (1.)  /Align 0 ]
        [ /Width 180 /FixHeight 07 /Margins  [0 0 0 0] /TextAtt {F3} /CellText (This is a computer generated transaction confirmation, therefore carries no signature. The validity of this confirmation is subject to the clearance of your cheque(s), if applicable.)  /Align 0 ]
        ] SHROW

        01 NL
        [ [ /Width 05  /FixHeight 07 /Margins  [0 0 0 0] /TextAtt {F3} /CellText (2.)  /Align 0 ]
        [ /Width 180 /FixHeight 07 /Margins  [0 0 0 0] /TextAtt {F3} /CellText (The items and figures shown above is considered correct unless we receive a written notification of any discrepancy within 7 business days from the date this confirmation is issued.)  /Align 0 ]
        ] SHROW	 } ENDIF

    %--------------------
    IF VAR_TRT (redemption) eq  {

        % insert footer
        04 SETLSP
        F3 12 253 MOVETO (Please note:) SHL
        01 NL
        [ [ /Width 05  /FixHeight 07 /Margins  [0 0 0 0] /TextAtt {F3} /CellText (1.)  /Align 0 ]						% tenure
        [ /Width 180 /FixHeight 07 /Margins  [0 0 0 0] /TextAtt {F3} /CellText (This is a computer generated transaction confirmation, therefore carries no signature. The validity of this confirmation is subject to the clearance of your cheque(s), if applicable.) /Align 0 ]
        ] SHROW

        01 NL
        [ [ /Width 05  /FixHeight 07 /Margins  [0 0 0 0] /TextAtt {F3} /CellText (2.) VSUB4 /Align 000020 ]						% tenure
        [ /Width 180 /FixHeight 07 /Margins  [0 0 0 0] /TextAtt {F3} /CellText (The items and figures shown above is considered correct unless we receive a written notification of any discrepancy within 7 business days from the date this confirmation is issued.)  /Align 0 ]
        ] SHROW	 } ENDIF

    %----------------------------------------
    IF VAR_TRT (internal unit trust transfer) eq  {

        % insert footer
        04 SETLSP
        F3 12 253 MOVETO (Please note:) SHL
        01 NL
        [ [ /Width 05  /FixHeight 07 /Margins  [0 0 0 0] /TextAtt {F3} /CellText (1.)  /Align 0 ]
        [ /Width 180 /FixHeight 07 /Margins  [0 0 0 0] /TextAtt {F3} /CellText (This is a computer generated transaction confirmation, therefore carries no signature.) /Align 0 ]
        ] SHROW

        01 NL
        [ [ /Width 05  /FixHeight 07 /Margins  [0 0 0 0] /TextAtt {F3} /CellText (2.)  /Align 0 ]
        [ /Width 180 /FixHeight 07 /Margins  [0 0 0 0] /TextAtt {F3} /CellText (The items and figures shown above is considered correct unless we receive a written notification of any discrepancy within 7 business days from the date this confirmation is issued.) /Align 0 ]
        ] SHROW	 } ENDIF

    %----------------------------------
    IF VAR_TRT (external unit trust transfer) eq  {

        % insert footer
        04 SETLSP
        F3 12 253 MOVETO (Please note:) SHL
        01 NL
        [ [ /Width 05  /FixHeight 07 /Margins  [0 0 0 0] /TextAtt {F3} /CellText (1.)  /Align 0 ]
        [ /Width 180 /FixHeight 07 /Margins  [0 0 0 0] /TextAtt {F3} /CellText (This is a computer generated transaction confirmation, therefore carries no signature.) /Align 0 ]
        ] SHROW

        01 NL
        [ [ /Width 05  /FixHeight 07 /Margins  [0 0 0 0] /TextAtt {F3} /CellText (2.) VSUB4 /Align 000020 ]						% tenure
        [ /Width 180 /FixHeight 07 /Margins  [0 0 0 0] /TextAtt {F3} /CellText (The items and figures shown above is considered correct unless we receive a written notification of any discrepancy within 7 business days from the date this confirmation is issued.) 	VSUB4 /Align 000020 ]                        			% due date
        ] SHROW	 } ENDIF

    % insert enquiries information

} %FSHOW

%%EOF
