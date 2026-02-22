%!
%%Title: SIBS_CASTF.FRM
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

        % June 2023
        10.7 16.2 MOVETO (OCBC.eps) CACHE 0.38  SCALL

        131.3 04  MOVETO F7 (OCBC Bank (Malaysia) Berhad 199401009721 (295400-W)) SHL

        03 SETLSP
        131.3 11 MOVETO  F6  (Personal Banking Enquiries  03-8317 5000                         )    SHL
        (Business Banking Enquiries 1300-88-7000 / 03-8317 5200)    SHL

        % Draw a horizontal line
        12 17 187 0.2 R_S1 DRAWB

        %Insert Statement type

        FA
        02.5 SETLSP
        12 21 MOVETO
        (STATEMENT OF $$VAR_CAE.) VSUB 0 SHP

        0.3 NL
        FC
        (PENYATA AKAUN $$VAR_ASB.) VSUB 0 SHP

        0.3 NL
        F8
        (Protected by PIDM up to RM250,000 for each depositor) VSUB 0 SHP

        % CC by Lian 20120116
        F7
        63 254.5 MOVETO
        (BASE LENDING RATE  $$VAR_BLR.% p.a.  WITH EFFECT FROM  $$VARMdate. $$VARMmonth. $$VARMyear.) VSUB SHL

        01 NL
        F4
        (KADAR PINJAMAN ASAS                          BERKUATKUASA DARI) SHL

        % Insert Marketing Message
        11 204 188 47 S2 DRAWB

        11.9 250.5 MOVETO
        12.3 200.8 185 43 CLIP DRAWB
        (OCBC_MSG.jpg) CACHE [185 44] 0 222 SCALL
        ENDCLIP

    } ENDIF

    IF VAR_ICAST (ICAST) eq

    {

        % June 2023
        10 16.5 MOVETO (OCBC Al-Amin.eps) CACHE 0.46  SCALL

        131.3 04 MOVETO F7 (OCBC Al-Amin Bank Berhad 200801017151 (818444-T)) SHL

        03 SETLSP
        131.3 11 MOVETO  F6  (Personal Banking Enquiries  03-8314 9310                         )    SHL
        (Business Banking Enquiries 1300-88 0255 / 03-8314 9090)    SHL

        % Draw a horizontal line
        12 17 187 0.2 R_S1 DRAWB

        %Insert Statement type

        FA
        02.5 SETLSP
        12 21 MOVETO
        (ISLAMIC BANKING: STATEMENT OF $$VAR_CAE.) VSUB 0 SHP

        0.3 NL
        FC
        (PERBANKAN ISLAM: PENYATA AKAUN $$VAR_ASB.) VSUB 0 SHP

        0.3 NL
        F8
        (Protected by PIDM up to RM250,000 for each depositor) VSUB 0 SHP

        % CC by Lian 20120116
        F7
        63 254.5 MOVETO
        (BASE FINANCING RATE  $$VAR_BLR.% p.a.  WITH EFFECT FROM  $$VARMdate. $$VARMmonth. $$VARMyear.) VSUB SHL

        01 NL
        F4
        (KADAR PEMBIAYAAN ASAS                          BERKUATKUASA DARI) SHL

        % Insert Marketing Message
        11 204 188 47 S2 DRAWB

        11.9 250.5 MOVETO
        12.3 200.8 185 43 CLIP DRAWB
        (ALAMIN_MSG.jpg) CACHE [185 43] 0 222 SCALL
        ENDCLIP

    } ENDIF

    % cc by lian 20120202
    FE
    04 SETLSP
    18 32 MOVETO
    VAR_ABC  180	0	SHP
    VAR_CN1  180	0	SHP
    VAR_CN2  180	0	SHP
    VAR_CN3  180	0	SHP
    VAR_AD1  180	0	SHP
    VAR_AD2	 180	0	SHP
    VAR_AD3	 180	0	SHP
    VAR_AD4	 180	0	SHP

    12 70 MOVETO
    (~~FAAccount Branch / ~~FBCawangan Akaun ~~FA: $$VAR_BRC.) VSUB 0 SHP

    200 70 MOVETO
    (~~FAStatement Date / ~~FBTarikh Penyata ~~FA: $$VAR_SSD. TO $$VAR_SED.) VSUB 1 SHP

    12 73.5 MOVETO
    (~~FAAccount Number / ~~FBNombor Akaun    ~~FA: $$VAR_ACN.) VSUB 0 SHP

    12 75.5 MOVETO
    (TXNB) SCALL

    % define txn lines
    03.5 NL
    F7
    14    MOVEH (Transaction Date)			SH
    38    MOVEH (Transaction Description)  	SH
    84    MOVEH (Cheque No.)				SH
    130   MOVEH (Withdrawal)		 		SHr
    162   MOVEH (Deposit) 					SHr
    193	MOVEH	(Balance)					SHr
    F8
    3.3 NL
    14    MOVEH (Tarikh Transaksi)			SH
    38    MOVEH (Huraian Transaksi)			SH
    84    MOVEH (No. Cek)					SH
    130   MOVEH (Pengeluaran)				SHr
    162   MOVEH (Deposit)					SHr
    193	MOVEH	(Baki)						SHr

    % Modified by Lian 02.12.2014
    F3
    2.5 SETLSP
    12 258 MOVETO
    (INSURANCE) SHL

    F3
    2.5 SETLSP
    12 261 MOVETO
    (If the property or asset that has been assigned or charged as security is non-landed, we request you to liaise with the relevant Joint Management Body (JMB) or Management Corporation (MC) to obtain the Certificate of Insurance for your unit or parcel. This is to ensure that your JMB/MC has indeed insured and keeps insured the building up to the replacement value of the building against fire and other such risks as may be required.) 187 3 SHP

    % Correction on foot note from "shall be deemed as aaaa correct, binding," to "shall be deemed as correct, binding,"
    F3
    2.5 SETLSP
    12 269 MOVETO
    (Local cheques etc. although passed to credit are accepted for collection only and will not be available until cleared. The entries and balance shown in this statement should be verified and the bank notified in writing of any errors or discrepancies within 14 days from the date of this statement. If the Bank does not receive any notification within the stipulated time, the entries in this statement shall be deemed as correct, binding, final and conclusive. Please notify us in writing for any change of address, telephone numbers and/or other personal details.) 187 3 SHP

    F4
    0.5 NL
    (Cek-cek tempatan dan sebagainya, yang telah dikreditkan ke dalam akaun tidak boleh digunapakai sehingga cek-cek tersebut dijelaskan. Butir-butir transaksi dan baki yang ditunjukkan di dalam penyata ini harus disemak dan sebarang kesilapan atau ketidaksamaan harus dimaklumkan kepada pihak Bank secara bertulis dalam tempoh 14 hari dari tarikh penyata ini. Jika pihak Bank tidak menerima sebarang maklumbalas dalam tempoh tersebut, segala butir-butir di dalam penyata ini adalah dianggap betul, terikat dan muktamad. Sila maklumkan kepada kami secara bertulis sebarang pertukaran alamat, nombor telefon dan/atau maklumat peribadi lain.) 187 3 SHP

    % Insert URL text
    F2
    1.5 SETLSP

    % Insert Group Name
    F2
    B
    199 290 MOVETO
    (A Member of OCBC Group) SHR

    R
    NL
    (https://www.ocbc.com.my) SHR
    B

}
