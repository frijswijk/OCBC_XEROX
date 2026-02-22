%!
%%Title: CASIOF3.FRM
%%Creator: Lian
%%CreationDate: Mon Jun 15 2009, 14:28:30.
%%EndComments

{  %%Begin Form
    XGF
    MM SETUNIT
    ORITL
    PORT
    2 SETLSP

    % Define Font Indexing
    (**) 2 SETFTSW
    /F1  /ARIALB   07  INDEXFONT
    /F2  /ARIAL    06  INDEXFONT
    /F3  /ARIAL    08  INDEXFONT
    /F4  /ARIALB   09  INDEXFONT
    /F5  /ARIALBO  07  INDEXFONT
    /F6  /ARIAL    07  INDEXFONT
    /F7  /ARIALB   08  INDEXFONT
    /F8  /ARIALO   07  INDEXFONT
    /F9  /ARIALBO  08  INDEXFONT

    % Define Color Indexing
    /B    BLACK        INDEXCOLOR
    /R    RED          INDEXCOLOR

    % June 2023
    10 16 MOVETO (OCBC.eps) CACHE 0.38  SCALL

    131.3 04  MOVETO F1 (OCBC Bank (Malaysia) Berhad 199401009721 (295400-W)) SHL

    % Insert Company Name
    F6

    % Draw a horizontal line
    12 17 187 0.2 R_S1 DRAWB

    % June 2023
    03 SETLSP
    131.3 11 MOVETO  F6  (Personal Banking Enquiries  03-8317 5000                         )    SHL
    (Business Banking Enquiries 1300-88-7000 / 03-8317 5200)    SHL

    02 SETLSP

    % Insert Statement Text
    105 22 MOVETO
    F4
    (STATEMENT OF ACCOUNT) SHC
    02 NL
    F9
    (PENYATA AKAUN)        SHC

    % Insert Your Monthly Transaction Details
    NL
    10 31 MOVETO
    F7
    (Your Monthly Transaction Details /)  SH
    F8
    (Transaksi Bulanan Anda)  SH
    F7
    ( - )  SH

    % Insert Variables - Customer Name
    88 31 MOVETO
    F7
    VAR_CN1  80 0 SHP

    % Insert Header
    10  33  189  15  LT     DRAWB % Shaded Box
    28  33   01  15  FWHITE DRAWB
    48  33   01  15  FWHITE DRAWB
    165 33   01  15  FWHITE DRAWB

    F7
    03.5  NL
    -69    MOVEHR (Transaction)   SHc
    03  NL
    -69    MOVEHR (Date)    SHc

    -03 NL
    -49.5    MOVEHR (Posting) SHc
    03  NL
    -49.5    MOVEHR (Date)    SHc

    -03 NL
    15     MOVEHR (Transaction Description)   SHc
    95     MOVEHR (Amount (RM))               SHc

    06  NL
    F8
    -69    MOVEHR (Tarikh) SHc
    03  NL
    -69    MOVEHR (Transaksi) SHc

    -03 NL
    -49.5    MOVEHR (Tarikh Bil) SHc
    03  NL
    -49.5    MOVEHR (Diterima) SHc

    -05 NL
    15     MOVEHR (Deskripsi Transaksi)       SHc
    95     MOVEHR (Amaun (RM))                SHc

    % Insert URL text
    F6 B

    % Insert Group Name
    F6 B
    186.5 290 MOVETO
    (A Member of OCBC Group) SHC

    R 01 NL (https://www.ocbc.com.my) SHC B

    % 20210427

}  % FSHOW
