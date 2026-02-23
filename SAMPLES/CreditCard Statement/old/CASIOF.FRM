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

% Define Dynamic Elements
% ------------------------------------------------
% Summary Account Box - prefix for B0
/SABX	{  02          00        84          08     LMED     DRAWB % Shaded Box
		   86          00     0.001          78     XDRK     DRAWB % Left Vertical Line
		   02          00     0.001          78     XDRK     DRAWB % Right Vertical Line
		  %52         -08	  0.001	       85.3     XDRK	 DRAWB % Middle Vertical Line
		   02          00        84       0.001     XDRK     DRAWB % First Horizontal Line
		   02         -08        84       0.001     XDRK     DRAWB % Second Horizontal ine
		   02         -62.5      84       0.001     XDRK     DRAWB % Third Horizontal Line
		  %02         -70        84       0.001     XDRK     DRAWB % Fourth Horizontal Line
		   02         -78        84       0.001     XDRK     DRAWB % Fifth Horizontal Line
		} XGFRESDEF		% Account Summary Box

% Credit Limits Box - prefix for C0 
/CLBX	{  %00          00       80        10.5      LMED     DRAWB % Shaded Box
		   % 2011-09-26
		   00          00       80          10      LMED     DRAWB % Shaded Box
		   80          00     0.001         26      XDRK     DRAWB % Left Vertical Line
		   00          00     0.001         26      XDRK     DRAWB % Right Vertical Line
		   00          00       80       0.001      XDRK     DRAWB % Top Hoizontal Line
		   %00         -10.5     80       0.001      XDRK     DRAWB % Middle 1 Horizontal Line
		   % 2011-09-26
		   00         -10       80       0.001      XDRK     DRAWB % Middle 1 Horizontal Line
		   %00         -17      80       0.001      XDRK     DRAWB % Middle 2 Horizontal Line
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

% HEADER -----------------------------------------
% ------------------------------------------------

% Insert Company Logo
% ------------------------------------------------
% 08 01.5 MOVETO
%  08 01 MOVETO
%  (OCBC-LOGO.TIF) 0.16 0 ICALL

% June 2023
%11 0.80 MOVETO	(OCBC.JPG) 0.45 0 ICALL
%10 0 MOVETO (OCBC.tif) 0.38 0 ICALL
%June 2023
10 16 MOVETO (OCBC.eps) CACHE 0.38  SCALL			

%131.3 05.2 MOVETO F1 (OCBC Bank (Malaysia) Berhad (199401009721 / 295400-W)) SHL
131.3 04  MOVETO F1 (OCBC Bank (Malaysia) Berhad 199401009721 (295400-W)) SHL

% Insert Company Name
% ------------------------------------------------
 F6
 %20.5 12.5 MOVETO
 % 23.5 15 MOVETO
 %(OCBC Bank (Malaysia) Berhad (199401009721 / 295400-W)) SHL

% Draw a horizontal line
 %08 15 193 0.2 R_S1 DRAWB
 %08 17 193 0.2 R_S1 DRAWB
 %12 17 187 0.2 R_S1 DRAWB
 %June 2023
 12 17 187 0.2 R_S1 DRAWB 

% Insert Enquiries Information
% ------------------------------------------------
% F1
% 201 08.5 MOVETO
% (Personal Banking Enquiries  03-8317 5000                         )    SHR
% NL
% (Business Banking Enquiries 1300-88-7000 / 03-8317 5200)    SHR

% June 2023
03 SETLSP
131.3 11 MOVETO  F6  (Personal Banking Enquiries  03-8317 5000                         )    SHL  
(Business Banking Enquiries 1300-88-7000 / 03-8317 5200)    SHL

02 SETLSP

% Insert Statement of Account Text
% ------------------------------------------------
 %105 20 MOVETO
 105 22 MOVETO
 F4
 (STATEMENT OF ACCOUNT) SHC
 02 NL
 F7
 (PENYATA AKAUN)        SHC

% Draw Box for Account Summary
% ------------------------------------------------
 %115 26 MOVETO
  115 28 MOVETO
  (SABX)SCALL		

% Insert Customer Variables
% ------------------------------------------------
  F8
  18.5 30 MOVETO
  05 SETLSP

 VAR_CN1  90  0  SHP
%VAR_CN2  90  0  SHP
 VAR_AD1  90  0  SHP
 VAR_AD2  90  0  SHP
 VAR_AD3  90  0  SHP
 VAR_AD4  90  0  SHP
 VAR_AD5  90  0  SHP
 VAR_PCS  90  0  SHP

% Draw Box for Credit Limit
% ------------------------------------------------
 %08 78.1 MOVETO
  08 80.1 MOVETO
 % 08 76  MOVETO
 (CLBX)SCALL		

% Insert IF / ELSE for WITHOUT PREJUDICE - B0
% ------------------------------------------------
 IF VAR_PDD (IMMEDIATE) eq
  {		  
    % Insert the word 'WITHOUT PREJUDICE' if IMMEDIATE display at Payment Due Date
    FB
    %201 20 MOVETO
     201 22 MOVETO
    ("WITHOUT PREJUDICE") SHR
		   
    % Insert the word 'Payments Accepted 'Without Prejudice' if IMMEDIATE display at Payment Due Date
    FB
    201 210.5 MOVETO
   (Payments Accepted 'Without Prejudice') SHR   
	    
 } ENDIF

% Insert Tiff Image File and Stretch-in-Box	
% ------------------------------------------------
% 08 124 193 47 S2 DRAWB

% 2011-09-26
08 124 193 77 S2 DRAWB
		
% 09 170 MOVETO
		
% 09.5 125 191 45.5 CLIP DRAWB
		
% (Promotion1.jpg) CACHE [191 45] 0 222 SCALL

% ENDCLIP

% Insert Dunning Message
% ------------------------------------------------
% 03.3 SETLSP
%57 NL
 %10 176 MOVETO
 %FD
 %U0
 %(Notice on Paying Only Minimum Monthly Repayment) [ 190 20 1.2 ] 3 SHP

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

% N0
% FE
% 0.5 NL
% (The amount of interest that you have to pay and the time it takes to repay your balance in full will increase if only the minimum monthly payment is made. Please refer to Table 1 at the back page which illustrates the amount of interest incurred and the repayment period, under different outstanding amount scenarios if you continue to pay only the minimum amount. The minimum monthly payment due is computed based on 5% balance outstanding or RM50, whichever is higher, at the applicable Tiered Interest charge. Please refer to overleaf for details.) [ 190  20 1.2 ] 3 SHP
% 0.5 NL
% FF
% U0
% (Notis Jika Hanya Membayar Bayaran Minimum Bulanan) [ 190 20 1.2 ] 3 SHP
% N0
% FG
% 0.5 NL
% (Jumlah faedah yang harus dibayar dan tempoh yang diambil untuk menjelaskan keseluruhan baki belum jelas anda akan bertambah jika anda hanya membayar bayaran minimum bulanan. Sila rujuk kepada Jadual 1 di muka surat belakang bagi gambaran jumlah faedah yang dikenakan dan tempoh pembayaran balik, bagi senario-senario baki belum jelas yang berbeza jika anda hanya membayar bayaran minimum secara berterusan. Pengiraan adalah berdasarkan 5% bayaran minimum atau RM50, yang mana lebih tinggi, mengikut Kadar Faedah Bertingkat Semasa. Sila rujuk di belakang untuk butiran lanjut.) [ 190  20 1.2 ] 3 SHP	

02 SETLSP

% Insert Proforation Line
% ------------------------------------------------
 00 204.3 210 0.01 B1 DRAWB

% Insert Cutter
% ------------------------------------------------
24 202.7 MOVETO
%05 NL
%14 MOVEHR
(SCISSORS.JPG) 0.06 0 ICALL
%Z <22> 180 S1 0 SHX
		
% Insert Cards Summary Text
% ------------------------------------------------
 10 210.5 MOVETO
%06 NL
%00 MOVEHR
 (**F5Payment Slip / **FCSlip Pembayaran) 0 SHmf
		
% Insert Cards Summary Box
% ------------------------------------------------
%04.5 NL
08 212.5 MOVETO
(CSBX) SCALL

% FOOTER
% ------------------------------------------------
% Insert Note Message for Page 1
% modified on 290709
% 10 267 MOVETO		
% 10 266.5 MOVETO

% 2011-09-26
%  10 266 MOVETO
% 20210427
  08 266 MOVETO
  (NOTE) SCALL

% Insert MEPS Logo
 % 10 284.5 MOVETO
 % 2011-09-26
 10 283 MOVETO
 %(OCBC-MEPS.JPG) 0.128 0 ICALL
 
 % 2011-09-26
 %(OCBC-MEPS2.jpg) 0.15 0 ICALL

% Insert URL text
% ------------------------------------------------
 F6 B 
  128 290 MOVETO
  %(Your banking questions ANSWERED! For more info,) SHC
  % 20210427
   %08 290 MOVETO (Your banking questions ANSWERED! For more info,) SHL
   %R  01 NL (log on to http://www.bankinginfo.com.my) SHL
 %R  01 NL (log on to http://www.bankinginfo.com.my) SHC

% Insert Group Name
% ------------------------------------------------
 F6
 B
  186.5 290 MOVETO (A Member of OCBC Group) SHC

  R 01 NL (https://www.ocbc.com.my) SHC B
 
  % 20210427
  %  201 290 MOVETO (A Member of OCBC Group) SHR
  %  R  01 NL (http://www.ocbc.com.my) SHR  B

} % FSHOW

%%EOF
