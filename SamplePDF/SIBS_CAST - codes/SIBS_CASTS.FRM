%!
%%Title: SIBS_CASTS.FRM
%%Creator: Lian 
%%CreationDate: Fri Apr 17 2009, 01:10:06.
%%EndComments

{  %%Begin Form

MM SETUNIT
ORITL
PORT
02 SETLSP

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

% Define Colour Indexing
% ------------------------------------------------
/B    	BLACK          	  INDEXCOLOR
/W    	WHITE          	  INDEXCOLOR
/R    	RED            	  INDEXCOLOR

% Define BatKey Indexing
% ------------------------------------------------
/U0 	/UNDL 			  INDEXBAT
/N0 	 null 			  INDEXBAT

% Define Dynamic Elements
% ------------------------------------------------
/TXNB  {  0   0    188    09  LMED     DRAWB} XGFRESDEF

% HEADER
IF VAR_CCAST (CCAST) eq
	{	
			% Insert Company Logo
			%12 14 MOVETO
			%(OCBC-LOGO.TIF) CACHE 0.14 0 SCALL
			
			% Insert Company Name
			%F2
			%26 13.5 MOVETO
			%(OCBC Bank (Malaysia) Berhad (295400-W)) SHL

  			%12 01 MOVETO
			%(OCBC-LOGO.TIF) 0.16 0 ICALL

			% June 2023			
			%10 0 MOVETO (OCBC.tif) 0.38 0 ICALL
			10.7 16.2 MOVETO (OCBC.eps) CACHE 0.38  SCALL		
					  				
    		131.3 04  MOVETO F7 (OCBC Bank (Malaysia) Berhad 199401009721 (295400-W)) SHL

			03 SETLSP
 			131.3 11 MOVETO  F6  (Personal Banking Enquiries  03-8317 5000                         )    SHL
 			(Business Banking Enquiries 1300-88-7000 / 03-8317 5200)    SHL    		
 			 			
 			%28 15 MOVETO F6 (OCBC Bank (Malaysia) Berhad (199401009721 / 295400-W)) SHL
   		
			% Insert Enquiries Information
			%F7
			%128 10.5 MOVETO
			%(Personal Banking Enquiries)    SHL
			
			%0.6 NL
			%(Business Banking Enquiries)    SHL
			
			%165 10.5 MOVETO
			%(1300-88 5000 / 03-8317 5000)   SHL
			
			%0.6 NL
			%(1300-88 7000 / 03-8317 5200)   SHL
	
			% Insert Enquiries Information
 			%199 08.5 MOVETO  F7  (Personal Banking Enquiries  03-8317 5000                         )    SHR
 			%NL  (Business Banking Enquiries 1300-88-7000 / 03-8317 5200)    SHR
 			
			% Draw a horizontal line
			%12 15 187 0.2 R_S1 DRAWB
			12 17 187 0.2 R_S1 DRAWB
	
			%165.5 27 MOVETO
			%(OCBC-MEPS2.jpg) CACHE 0.15 0 SCALL

			% CC by Lian 20120202
			%Insert Statement type

			FA
			02.5 SETLSP
			%12 18.3 MOVETO
			12 21 MOVETO
			(STATEMENT OF $$VAR_CAE.) VSUB 0 SHP
			
			0.3 NL
			FC
			(PENYATA AKAUN $$VAR_ASB.) VSUB 0 SHP
			
			0.3 NL
			F8
			(Protected by PIDM up to RM250,000 for each depositor) VSUB 0 SHP

		} ENDIF
		
		IF VAR_ICAST (ICAST) eq

		{
			% Insert Company Logo
			%12 14 MOVETO
			%(OCBC-AL-AMIN.jpg) CACHE 0.315 0 SCALL

			% Insert Company Name
			%F2
			%26 13.5 MOVETO
			%(OCBC Al-Amin Bank Berhad (818444-T)) SHL

			%12 02 MOVETO
			%(OCBC-AL-AMIN.jpg) 0.31 0 ICALL

			% June 2023	
			%9.5 -0.2 MOVETO (OCBC Al-Amin.tif) 0.46 0 ICALL
			10 16.5 MOVETO (OCBC Al-Amin.eps) CACHE 0.46  SCALL

    		131.3 04 MOVETO F7 (OCBC Al-Amin Bank Berhad 200801017151 (818444-T)) SHL

			03 SETLSP
 			131.3 11 MOVETO  F6  (Personal Banking Enquiries  03-8314 9310                         )    SHL 
 			(Business Banking Enquiries 1300-88 0255 / 03-8314 9090)    SHL
 			
 			%F6
 			%25.5 15 MOVETO
 			%(OCBC Al-Amin Bank Berhad (200801017151 / 818444-T)) SHL
 		
			%97.7 14 MOVETO
			%155 30 MOVETO
			%155 19 MOVETO
			%(PERBANKAN-ISLAM.jpg) 0.06 0 ICALL
			
			% Insert Enquiries Information
			%F7
			%128 10.5 MOVETO
			%(Personal Banking Enquiries)    SHL
			%0.6 NL
			%(Business Banking Enquiries)    SHL
			
			%165 10.5 MOVETO
			%(1300-88 0310 / 03-8314 9310)   SHL
			%0.6 NL
			%(1300-88 0255 / 03-8314 9090)   SHL

			% Insert Enquiries Information
 			%199 08.5 MOVETO  F7  (Personal Banking Enquiries  03-8314 9310                         )    SHR 
 			%NL  (Business Banking Enquiries 1300-88 0255 / 03-8314 9090)    SHR
 			 			
			% Draw a horizontal line
			%12 15 185 0.2 R_S1 DRAWB
			12 17 187 0.2 R_S1 DRAWB

			%164 17 MOVETO
			%164 27 MOVETO
			%(MEPS-ISLAMIC.jpg) CACHE 0.75 0 SCALL
						
			%148 MOVEH
			%(PERBANKAN-ISLAM.jpg) CACHE 0.06 0 SCALL

			% CC by Lian 20120202
			%Insert Statement type
			
			FA
			02.5 SETLSP
			%12 18.3 MOVETO
			12 21 MOVETO
			(ISLAMIC BANKING: STATEMENT OF $$VAR_CAE.) VSUB 0 SHP
			
			0.3 NL
			FC
			(PERBANKAN ISLAM: PENYATA AKAUN $$VAR_ASB.) VSUB 0 SHP	
			
			0.3 NL
			F8
			(Protected by PIDM up to RM250,000 for each depositor) VSUB 0 SHP			

		} ENDIF

% cc by lian 20120202
	FE
	04 SETLSP
	%18 29 MOVETO
	18 32 MOVETO
	VAR_ABC  180	0	SHP
	VAR_CN1  180	0	SHP
	VAR_CN2  180	0	SHP
	VAR_CN3  180	0	SHP
	VAR_AD1  180	0	SHP
	VAR_AD2	 180	0	SHP
	VAR_AD3	 180	0	SHP
	VAR_AD4	 180	0	SHP	
	%VAR_HMD	 180	0	SHP

	12 70 MOVETO
	(~~FAAccount Branch / ~~FBCawangan Akaun ~~FA: $$VAR_BRC.) VSUB 0 SHP

	200 70 MOVETO
	(~~FAStatement Date / ~~FBTarikh Penyata ~~FA: $$VAR_SSD. TO $$VAR_SED.) VSUB 1 SHP	

	12 73.5 MOVETO	
	(~~FAAccount Number / ~~FBNombor Akaun    ~~FA: $$VAR_ACN.) VSUB 0 SHP
	
	12 75.5 MOVETO
	(TXNB) SCALL

	% define txn lines  
	3.5 NL
	F7
	14    MOVEH (Transaction Date)			SH
	38    MOVEH (Transaction Description)  	SH
	84    MOVEH (Cheque No.)				SH
	130   MOVEH (Withdrawal)		 		SHr
	162   MOVEH (Deposit) 					SHr
	193  	MOVEH	(Balance)					SHr
	F8 
 	3.3 NL
	14    MOVEH (Tarikh Transaksi)			SH
	38    MOVEH (Huraian Transaksi)			SH
	84    MOVEH (No. Cek)					SH
	130   MOVEH (Pengeluaran)				SHr
	162   MOVEH (Deposit)					SHr
	193	  MOVEH	(Baki)						SHr

% FOOTER
% Insert URL text
F2
1.5 SETLSP
%B
%12 290 MOVETO
%(Your banking questions ANSWERED! For more info,) SHL
%NL
%12 MOVEH
%(log on to) SH
%R
%( http://www.bankinginfo.com.my) SH
%R
%NL
%(log on to http://www.bankinginfo.com.my) SHC

% Insert Group Name
F2
B
199 290 MOVETO
(A Member of OCBC Group) SHR

R
NL
(https://www.ocbc.com.my) SHR
B

} %FSHOW

