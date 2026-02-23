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

% Define Dynamic Elements
% ------------------------------------------------
% Year End Summary Box - prefix for YR
/YRSB	{	% 00   -14    173     08     FBLACK     DRAWB % Shaded Box
			% 20210427
			 00   -14    193     08     FBLACK     DRAWB % Shaded Box
		   	%00    00      192    0.001     XDRK     DRAWB % Top Horizontal Line
		   	%00   -35      192    0.001     XDRK     DRAWB % Bottom Horizontal Line  
			
		} XGFRESDEF		% Year End Summary
% HEADER -----------------------------------------
% ------------------------------------------------

% Insert Company Logo
% ------------------------------------------------
 %08 01.5 MOVETO
 %(OCBC-LOGO.TIF) 0.125 0 ICALL
 
 % 20210427
 %  08 01 MOVETO
 % (OCBC-LOGO.TIF) 0.16 0 ICALL
 
 % June 2023
 %11 0.80 MOVETO (OCBC.JPG) 0.45 0 ICALL			  				
 %131.3 05.2 MOVETO F1 (OCBC Bank (Malaysia) Berhad (199401009721 / 295400-W)) SHL

%June 2023
10 16 MOVETO (OCBC.eps) CACHE 0.38  SCALL
131.3 04  MOVETO F1 (OCBC Bank (Malaysia) Berhad 199401009721 (295400-W)) SHL

% Insert Company Name
% ------------------------------------------------
 %F2
 % 20.5 12.5 MOVETO
 % (OCBC Bank (Malaysia) Berhad (295400-W)) SHL
 
 % 20210427
 % F6 23.5 15 MOVETO
 % (OCBC Bank (Malaysia) Berhad (199401009721 / 295400-W)) SHL

% Draw a horizontal line
% 08 15 193 0.2 R_S1 DRAWB

% 20210427
% 08 17 193 0.2 R_S1 DRAWB
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

% Insert Statement of Account Text
% ------------------------------------------------
% modified on 24/10/2011
% 105 20 MOVETO
% F4
% (STATEMENT OF ACCOUNT) SHC
% 02 NL
% F7
% (PENYATA AKAUN)        SHC

% Draw Box for Year End Account Summary
% ------------------------------------------------
% 115 30 MOVETO
% (YESB)SCALL		
%18.5 50 MOVETO

% 20210427
  08 50 MOVETO
 (YRSB)SCALL

% 21 69.5 MOVETO
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
%VAR_CN2  90  0  SHP
 VAR_AD1  90  0  SHP
 VAR_AD2  90  0  SHP
 VAR_AD3  90  0  SHP
 VAR_AD4  90  0  SHP
 VAR_AD5  90  0  SHP
 VAR_PCS  90  0  SHP

% Draw Box for Payment Information
% ------------------------------------------------
%  08 55 MOVETO
%  (YESB)SCALL

%  12 62 MOVETO
%  W
%  FH
%  (Summary of Account Activity for $$VAR_SAAF.) VSUB SH

%  08 160 MOVETO
%  (YESB)SCALL

%  12 166 MOVETO
%  W
%  FH
%  (Payment Information) VSUB SH

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
 03 SETLSP
 128 290 MOVETO
 %(Your banking questions ANSWERED! For more info,) SHC
 %R   (log on to http://www.bankinginfo.com.my) SHC
 01 NL
 
  % 20210427
  % 08 290 MOVETO (Your banking questions ANSWERED! For more info,) SHL
  % R  01 NL (log on to http://www.bankinginfo.com.my) SHL

% Insert Group Name
% ------------------------------------------------
 F6  B  186.5 290 MOVETO  (A Member of OCBC Group) SHC

 R  (https://www.ocbc.com.my) SHC  B
 01 NL
 
 % 10 0 MOVETO

  % 20210427
  %  F6  B  201 290 MOVETO (A Member of OCBC Group) SHR
  %  R  01 NL (http://www.ocbc.com.my) SHR  B

} % FSHOW

%%EOF
