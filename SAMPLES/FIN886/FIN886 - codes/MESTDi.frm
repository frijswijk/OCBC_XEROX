%!
%%Title: MESTDi.frm
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
%12 01.5 MOVETO
%(OCBC-AL-AMIN.jpg) 0.33 0 ICALL

%F6
%26 15 MOVETO
%(OCBC Al-Amin Bank Berhad (200801017151 / 818444-T)) SHL
 	 		
%155 19.5 MOVETO
%(PERBANKAN-ISLAM.jpg) 0.06 0 ICALL
    		
% Insert Enquiries Information
%199 08.5 MOVETO  F7  (Personal Banking Enquiries  03-8317 5000                         )    SHR
%NL  (Business Banking Enquiries 1300-88-7000 / 03-8317 5200)    SHR
 				
% Draw a horizontal line
%12 15 187 0.2 R_S1 DRAWB
%12 17 187 0.2 R_S1 DRAWB
	
%165.5 17 MOVETO
%(OCBC-MEPS2.jpg) .15 0 ICALL

			% June 2023	
			%9.5 -0.2 MOVETO (OCBC Al-Amin.tif) 0.46 0 ICALL
			10 16.5 MOVETO (OCBC Al-Amin.eps) CACHE 0.46  SCALL

    		131.3 04 MOVETO F7 (OCBC Al-Amin Bank Berhad 200801017151 (818444-T)) SHL

			03 SETLSP
 			131.3 11 MOVETO  F6  (Personal Banking Enquiries  03-8314 9310                         )    SHL 
 			(Business Banking Enquiries 1300-88 0255 / 03-8314 9090)    SHL
			
			% Draw a horizontal line
			12 17 187 0.2 R_S1 DRAWB

% CC by Lian 20120202
%Insert Statement type

FA
02.5 SETLSP
%12 18.3 MOVETO
12 21 MOVETO
(STATEMENT OF LOAN ACCOUNT) VSUB 0 SHP
			
0.3 NL
FC
(PENYATA AKAUN PINJAMAN) VSUB 0 SHP

11.9 253.5 MOVETO
12.3 209.8 185 43 CLIP DRAWB
%(OCBC_MSG.jpg) CACHE [185 44] 0 222 SCALL
ENDCLIP


	12 70 MOVETO
	(~~FAAccount Branch / ~~FBCawangan Akaun ~~FA:) 0 SHMF

	120 70 MOVETO
	(~~FAAccount Type / ~~FBJenis Account ~~FA     :)  0 SHMF	
	
	12 73.5 MOVETO
	(~~FAAccount Number / ~~FBNombor Akaun    ~~FA:) 0 SHMF

	120 73.5 MOVETO
	(~~FAStatement Date / ~~FBTarikh Penyate  ~~FA:) 0 SHMF

	12 75.5 MOVETO
	(TXNB) SCALL
	
	% define txn lines  
	3.5 NL
	F7
	21    MOVEH (Date)						SH
	44    MOVEH (Transaction Description)  	SH
	131   MOVEH (Debit)		 				SHr
	165   MOVEH (Credit) 					SHr
	197	  MOVEH	(Balance)					SHr
	F8
 	3.3 NL
	21    MOVEH (Tarikh)			SH
 	44    MOVEH (Huraian Transaksi)	SH
	131   MOVEH (Debit)				SHr
	165   MOVEH (Kredit)			SHr
	197	  MOVEH	(Baki)						SHr

% LCY - 1st November 2013 - Tiffany reported
% Correction on foot note from "shall be deemed as aaaa correct, binding," to "shall be deemed as correct, binding,"
	
F3
2.5 SETLSP
12 258.7 MOVETO
(INSURANCE) SHL

0.5 NL
(If the property or asset that has been assigned or changed as security is non-landed, we request you to liaise with the relevant Joint Management Body (JMB) or Management Corporation (MC) to obtain the Certificate of Insurance for your unit or parcel. This is to ensure that your JMB/MC has indeed insured and keeps insured the building up to the replacement value of the building against fire and other such risks as may be required.) 187 3 SHP

01 NL
(Local cheques etc, although passed to credit are accepted for collection only and will not be available until cleaned. The entries and balance shown in this statement should be verified and the bank notified in writing of any errors or discrepancies within 14 days from the date of this statement. If the Bank does not receive any notification within the stipulated time, the enteries in this statement shall be deemed as correct, binding, final and conclusive. Please notify us in writing for any change of address, telephone numbers and/or other personal details.) 187 3 SHP

F4
0.5 NL
(Cek-cek tempatan dan sebagainya, yang telah dikreditkan ke dalam akaun tidak boleh digunapakai sehingga cek-cek tersebut dijelaskan. Butir-butir transaksi dan baki yang ditunjukkan di dalam penyata ini harus disemak dan sebarang kesilapan atau ketidaksamaan harus dimaklumkan kepada pihak Bank secare bertulis dalam  tempoh 14 hari dari tarikh penyata ini. Jika pihak Bank tidak menerima sebarang maklumbalas dalam tempoh tersebut, segala butir-butir di dalam penyata ini adalah dianggap betul, terikat dan muktamad. Sila maklumkan kepada kami secara bertulis sebarang pertukaran alamat, nombor telefon dan/atau maklumat peribadi lain.) 187 3 SHP

% FOOTER
% Insert URL text
F2
1.5 SETLSP
B
12 290 MOVETO
(Your banking questions ANSWERED! For more info,) SHL
NL
12 MOVEH
(log on to) SH
R
( http://www.bankinginfo.com.my) SH
R
NL
%(log on to http://www.bankinginfo.com.my) SHC

% Insert Group Name
F2
B
199 290 MOVETO
(A Member of OCBC Group) SHR

R
NL
(http://www.ocbc.com.my) SHR
B

} FSHOW

