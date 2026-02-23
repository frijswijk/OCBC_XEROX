%!
%%Title: CASIOF.FRM
%%Creator: Lian
%%CreationDate: Mon Jun 15 2009, 14:28:30.
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
    % Summary Account Box - prefix for B0
    /SABX	{  02          00        84          08     LMED     DRAWB % Shaded Box
        86          00     0.001          78     XDRK     DRAWB % Left Vertical Line
        02          00     0.001          78     XDRK     DRAWB % Right Vertical Line
        02          00        84       0.001     XDRK     DRAWB % First Horizontal Line
        02         -08        84       0.001     XDRK     DRAWB % Second Horizontal ine
        02         -62.5      84       0.001     XDRK     DRAWB % Third Horizontal Line
        02         -78        84       0.001     XDRK     DRAWB % Fifth Horizontal Line
    } XGFRESDEF		% Account Summary Box

    % Credit Limits Box - prefix for C0
    /CLBX	{  %00          00       80        10.5      LMED     DRAWB % Shaded Box
        % 2011-09-26
        00          00       80          10      LMED     DRAWB % Shaded Box
        80          00     0.001         26      XDRK     DRAWB % Left Vertical Line
        00          00     0.001         26      XDRK     DRAWB % Right Vertical Line
        00          00       80       0.001      XDRK     DRAWB % Top Hoizontal Line
        % 2011-09-26
        00         -10       80       0.001      XDRK     DRAWB % Middle 1 Horizontal Line
        00         -26       80       0.001      XDRK     DRAWB % Bottom Horizontal Line
    } XGFRESDEF		% Credit Limit Box

    % Define Dynamic Elements for Note
    % ------------------------------------------------
    /NOTE	{
        (**F5NOTE / **FCNOTA:) 0 SHmf
        04 NL
        F3
        (Please issue separate cheque payment(s) for each of your card account(s) when mailing with this payment slip. Kindly detach this portion and return it with your cheque made payable to **FBOCBC Card for **U0< YOUR NAME >**N0**F3.) [ 193 20 1.3 ] 3 SHp

        04 NL
        (**FCSila sediakan cek pembayaran yang berasingan untuk setiap kad akaun anda apabila menghantar bersama slip pembayaran ini. Sila leraikan bahagian ini dan kembalikan bersama cek anda yang dibayar ke **F5Kad OCBC untuk **U0< NAMA ANDA >**N0 **F3.) [ 193 20 1.3 ] 3 SHp
    } XGFRESDEF		% Note Message for Page 1

    %June 2023
    10 16 MOVETO (OCBC.eps) CACHE 0.38  SCALL

    131.3 04  MOVETO F1 (OCBC Bank (Malaysia) Berhad 199401009721 (295400-W)) SHL

    % Insert Company Name
    % ------------------------------------------------
    F6

    %June 2023
    12 17 187 0.2 R_S1 DRAWB

    % June 2023
    03 SETLSP
    131.3 11 MOVETO  F6  (Personal Banking Enquiries  03-8317 5000                         )    SHL
    (Business Banking Enquiries 1300-88-7000 / 03-8317 5200)    SHL

    02 SETLSP

    % Insert Statement of Account Text
    % ------------------------------------------------
    105 22 MOVETO
    F4
    (STATEMENT OF ACCOUNT) SHC
    02 NL
    F7
    (PENYATA AKAUN)        SHC

    % Draw Box for Account Summary
    % ------------------------------------------------
    115 28 MOVETO
    (SABX)SCALL

    % Insert Customer Variables
    % ------------------------------------------------
    F8
    18.5 30 MOVETO
    05 SETLSP

    VAR_CN1  90  0  SHP
    VAR_AD1  90  0  SHP
    VAR_AD2  90  0  SHP
    VAR_AD3  90  0  SHP
    VAR_AD4  90  0  SHP
    VAR_AD5  90  0  SHP
    VAR_PCS  90  0  SHP

    % Draw Box for Credit Limit
    % ------------------------------------------------
    08 80.1 MOVETO
    (CLBX)SCALL

    % Insert IF / ELSE for WITHOUT PREJUDICE - B0
    % ------------------------------------------------
    IF VAR_PDD (IMMEDIATE) eq
    {
        % Insert the word 'WITHOUT PREJUDICE' if IMMEDIATE display at Payment Due Date
        FB
        201 22 MOVETO
        ("WITHOUT PREJUDICE") SHR

        % Insert the word 'Payments Accepted 'Without Prejudice' if IMMEDIATE display at Payment Due Date
        FB
        201 210.5 MOVETO
        (Payments Accepted 'Without Prejudice') SHR

    } ENDIF

    % 2011-09-26
    08 124 193 77 S2 DRAWB

    % 2011-09-26
    17 134 MOVETO
    FH
    (WARNING ON PAYING ONLY MINIMUM MONTHLY REPAYMENT) [ 182 20 1.3 ] 3 SHP

    02 NL
    FH
    (If you make only the minimum payment each period, you will pay more in interest and it will take you longer to pay off your outstanding balance. Please refer to Table 1 at the back page for more information. Alternatively, you may also refer to the credit card calculator available on OCBC website.) [ 175 20 1 ] 3 SHP

    06 NL
    FH
    (AMARAN JIKA HANYA MEMBAYAR BAYARAN MINIMA BULANAN) [ 182 20 1.3 ] 3 SHP

    02 NL
    FH
    (Jika anda hanya membayar bayaran minima bulanan, jumlah faedah yang harus dibayar dan tempoh yang diambil untuk menjelaskan keseluruhan baki tertunggak belum jelas anda akan bertambah. Sila rujuk kepada Jadual 1 di muka surat belakang untuk maklumat lanjut. Anda juga boleh merujuk kepada kalkulator kad kredit yang sedia ada di laman web OCBC.) [ 175 20 1 ] 3 SHP

    % FG

    02 SETLSP

    % Insert Proforation Line
    % ------------------------------------------------
    00 204.3 210 0.01 B1 DRAWB

    % Insert Cutter
    % ------------------------------------------------
    24 202.7 MOVETO
    (SCISSORS.JPG) 0.06 0 ICALL

    % Insert Cards Summary Text
    % ------------------------------------------------
    10 210.5 MOVETO
    (**F5Payment Slip / **FCSlip Pembayaran) 0 SHmf

    % Insert Cards Summary Box
    % ------------------------------------------------
    08 212.5 MOVETO
    (CSBX) SCALL

    % 20210427
    08 266 MOVETO
    (NOTE) SCALL

    % 2011-09-26
    10 283 MOVETO

    % Insert URL text
    % ------------------------------------------------
    F6 B
    128 290 MOVETO

    % Insert Group Name
    % ------------------------------------------------
    F6
    B
    186.5 290 MOVETO (A Member of OCBC Group) SHC

    R 01 NL (https://www.ocbc.com.my) SHC B

    % 20210427

} % FSHOW

%%EOF
