%!
%%Title: CASIOB2.FRM
%%Creator: Lian
%%CreationDate: Mon Jun 15 2009, 14:28:30.
%%EndComments

{  %%Begin Form

    % Form Layout Definitions
    % ------------------------------------------------
    XGF
    MM SETUNIT
    ORITL
    PORT
    1.5 SETLSP

    % Define Font Indexing
    % ------------------------------------------------
    (**) 02 SETFTSW
    /F1  /ARIALB   12	 INDEXFONT
    /F2  /ARIALB   07	 INDEXFONT
    /F3	 /ARIALB   08	 INDEXFONT
    /F4	 /ARIAL    05.5	 INDEXFONT
    /F5  /ARIALB   05.5  INDEXFONT
    /F6  /ARIALO   05.5  INDEXFONT
    /F7  /ARIALBO  05.5  INDEXFONT
    /F8  /ARIALBO  06.5  INDEXFONT
    /F9  /ARIALB   06.5  INDEXFONT
    /F0  /ARIALB   05.3  INDEXFONT
    /FA  /ARIAL    05.45 INDEXFONT
    /Z 	 /NZDB 	   04	 INDEXFONT

    % Define BatKey Indexing
    % ------------------------------------------------
    /U0 	 /UNDL 			INDEXBAT
    /N0 	  null 			INDEXBAT

    % ------------------------------------------------
    % Important Notes Table
    /INBX	{  00	    00		105		 04			LMED	 DRAWB % Shaded Box
        105      00		0.001	201	 		XDRK	 DRAWB % Right Vertical Line
        36	   -04		0.001  	197  		XDRK	 DRAWB % Middle Vertical Line
        00	    00		0.001	201			XDRK	 DRAWB % Left Vertical Line
        00	    00		 105	0.001		XDRK	 DRAWB % Top 1 Horizontal Line
        00	   -04	 	 105	0.001		XDRK	 DRAWB % Top 2 Horizontal Line
        65      -04      0.001    30	     	XDRK	 DRAWB % Table Vertical - Principal
        83      -04      0.001    30	     	XDRK	 DRAWB % Table Vertical - Supplementary
        36      -10.5      69    0.001		XDRK	 DRAWB % Gold
        36      -13.9      69    0.001		XDRK	 DRAWB % Great Eastern Classic
        36      -20.6      69    0.001		XDRK	 DRAWB % Titanium
        36      -27.2      69    0.001		XDRK	 DRAWB % Platinum Robinsons
        36      -30.5      69    0.001		XDRK	 DRAWB % Bottom Table Line
        00      -34       105    0.001       XDRK     DRAWB % Middle 1 Horizontal Line - Finance Charges
        00	   -82  	 105	0.001		XDRK	 DRAWB % Middle 2 Horizontal Line - Cash Advances
        00	   -96.1  	 105	0.001		XDRK	 DRAWB % Middle 3 Horizontal Line - Minimum Monthly
        00	   -101.5  	 105	0.001		XDRK	 DRAWB % Middle 4 Horizontal Line - Late Payment
        00	   -111.5 	 105	0.001		XDRK	 DRAWB % Middle 5 Horizontal Line - Interest Free
        00	   -134 	 105	0.001		XDRK	 DRAWB % Middle 6 Horizontal Line - Conversion
        00	   -152.5 	 105	0.001		XDRK	 DRAWB % Middle 7 Horizontal Line - Other Charges
        00	   -201 	 105	0.001		XDRK	 DRAWB % Middle 8 Horizontal Line - Bottom Line
    } XGFRESDEF		% Important Notes

    % Retail Purchase Table
    /EUBX	{  00	    00	  	  105 	    06		LMED	 DRAWB % Shaded Box
        105      00		0.001	    36	 	XDRK	 DRAWB % Right Vertical Line
        36	   -06		0.001  	    30		XDRK	 DRAWB % Middle 1 Vertical Line
        48	   -06		0.001  	    30		XDRK	 DRAWB % Middle 2 Vertical Line
        59	   -06		0.001  	    30		XDRK	 DRAWB % Middle 3 Vertical Line
        71	   -06		0.001  	    30		XDRK	 DRAWB % Middle 4 Vertical Line
        83	   -06		0.001  	    30		XDRK	 DRAWB % Middle 5 Vertical Line
        94	   -06		0.001  	    30		XDRK	 DRAWB % Middle 6 Vertical Line
        24.1	   -24		0.001  	    12		XDRK	 DRAWB % Middle 7 Vertical Line
        00	    00		0.001	    36		XDRK	 DRAWB % Left Vertical Line
        00	    00		  105 	 0.001		XDRK	 DRAWB % Top Horizontal Line
        36.1	   -18  	 68.8	    06		LMED	 DRAWB % Shaded Box	for Finance Charges
        00	   -06		  105	 0.001		XDRK	 DRAWB % Middle 1 Horizontal Line
        00	   -12		  105	 0.001		XDRK	 DRAWB % Middle 2 Horizontal Line
        00	   -18		  105	 0.001		XDRK	 DRAWB % Middle 3 Horizontal Line
        00	   -24		  105	 0.001		XDRK	 DRAWB % Middle 4 Horizontal Line
        00	   -27.5	  105	 0.001		XDRK	 DRAWB % Middle 5 Horizontal Line
        00	   -31.5	  105	 0.001		XDRK	 DRAWB % Middle 6 Horizontal Line
        00	   -36		  105	 0.001		XDRK	 DRAWB % Bottom Horizontal Line
    } XGFRESDEF		% Examples Under Different Outstanding Amount Scenarios

    % Insert Company Name and Registration Number
    % ------------------------------------------------
    F1
    204.1 14 MOVETO
    (OCBC Bank (M) Berhad)  SHR
    NL
    F2

    % Insert Important Notes Box
    06 20.5 MOVETO
    (INBX) SCALL

    % Insert Important Notes
    08.5 23.5 MOVETO
    (**F9IMPORTANT NOTES FOR CARDMEMBERS / **F8MAKLUMAT PENTING BAGI PEMEGANG KAD) 0 SHmf

    % Insert paragraph 1
    2.25 SETLSP

    % Insert Annual Fee for Visa/Mastercard
    07.5 33 MOVETO
    F4
    (Annual Fee) SH
    02.5 NL
    (Visa/MasterCard) SH

    F6
    02.5 NL
    (Yuran Tahunan) SH
    02.5 NL
    (Visa/MasterCard) SH

    % Insert Annual Fee for table
    55 27 MOVETO
    F4
    (Card Type) SHc

    02.5 NL
    F6
    (Jenis Kad) SHc

    F4
    04 NL
    (Gold) SHc
    03.3 NL
    (Great Eastern) SHc
    03.3 NL
    (Titanium) SHc
    03.3 NL
    (Great Eastern) SHc
    03.3 NL
    (Platinum) SHc
    03.3 NL
    (Titanium) SHc
    03.3 NL
    (Platinum) SHc

    80 27 MOVETO
    F4
    (Principal (RM)) SHc

    02.5 NL
    F6
    (Kad Asas (RM)) SHc

    F4
    04 NL
    (38) SHc
    4.95 NL
    (68) SHc
    1.65 NL
    () SHc
    4.95 NL
    (138) SHc
    1.65 NL
    () SHc
    03.3 NL
    (68) SHc
    03.3 NL
    (188) SHc

    100 27 MOVETO
    F4
    (Supplementary (RM)) SHc

    02.5 NL
    F6
    (Kad Tambahan (RM)) SHc

    F4
    04 NL
    (28) SHc
    4.95 NL
    (28) SHc
    1.65 NL
    () SHc
    4.95 NL
    (38) SHc
    1.65 NL
    () SHc
    03.3 NL
    (28) SHc
    03.3 NL
    (68) SHc

    07.5  57 MOVETO
    F4
    (**F4Finance Charges / **F6Caj Kewangan) 0 SHmf
    03 NL
    F4
    ((a))  SH
    35 NL
    ((b))  SH

    11.5 60 MOVETO
    (Retail Purchase (exclude Balance Transfer & Flexi Payment Plan)) [ 28 20 1.1 ] 0 SHP
    01 NL
    F6
    (Urusniaga Runcit (tidak termasuk Pemindahan Baki & Plan Pembayaran Flexi)) [ 28 20 1.1 ] 0 SHP

    11.5 95 MOVETO
    F4
    (Cash Advance / Casino Chips) [ 28 20 1.1 ] 3 SHP
    F6
    (Pendahuluan Wang Tunai / Cip Kasino) [ 28 20 1.1 ] 3 SHP

    % Insert paragraph 2
    7.5 109 MOVETO
    F4
    (Cash Advance/Casino Chip Fees) [ 28 20 1.1 ] 3 SHP
    F6
    (Yuran Pendahuluan Wang Tunai/Cip Kasino) [ 28 20 1.1 ] 3 SHP

    % Insert paragraph 3
    03.2 NL
    F4
    (Minimum Monthly Repayment) [ 28 20 1.1 ] 3 SHP
    F6
    (Bayaran Minima Bulanan) [ 28 20 1.1 ] 3 SHP

    % Insert paragraph 4
    03 NL
    F4
    (Late Payment Charge) [ 28 20 1.1 ] 3 SHP
    F6
    (Caj Pembayaran Lewat) [ 28 20 1.1 ] 3 SHP

    % Insert paragraph 5
    09 NL
    F4
    (Interest-free Period for Retail Purchases) [ 28 20 1.2 ] 3 SHP
    F6
    (Tempoh Tanpa Faedah bagi Urusniaga Runcit) [ 28 20 1.2 ] 3 SHP

    % Insert paragraph 6
    12 NL
    F4
    (Conversion for Overseas Transactions) [ 28 20 1.2 ] 3 SHP
    F6
    (Kadar Tukaran bagi Transaksi Luar Negara) [ 28 20 1.2 ] 3 SHP

    % Insert paragaph 7
    08 176 MOVETO
    F4
    (Other Charges) [ 28 20 1.1 ] 3 SHP
    ((a)   Statement Retrieval Fee) [ 28 20 1.1 ] 3 SHP
    3 NL
    ((b)   Transaction Receipts) [ 28 20 1.1 ] 3 SHP
    0.5  NL
    ((c)   Card Replacement Fee) [ 28 20 1.1 ] 3 SHP
    0.5  NL
    ((d)   Cheque Returned Fee) [ 28 20 1.1 ] 3 SHP
    0.5 NL
    ((e)   Over Limit Fee) [ 38 20 1.2 ] 3 SHP

    01.5  NL
    F6
    (Caj Lain-lain) [ 38 20 1.2 ] 3 SHP
    ((a)   Caj bagi pengeluaran penyata) [ 38 20 1.2 ] 3 SHP
    03 NL
    ((b)   Resit Transaksi) [ 38 20 1.2 ] 3 SHP
    0.5 NL
    ((c)   Caj Penggantian Kad) [ 38 20 1.2 ] 3 SHP
    0.5 NL
    ((d)   Caj Cek Tak Laku) [ 38 20 1.2 ] 3 SHP
    0.5 NL
    ((e)   Caj Had Lebih) [ 38 20 1.2 ] 3 SHP

    % Insert notes for (a)
    45 57 MOVETO
    F4
    (Tier 1 - 13.5% p.a. in interest charge on the 13th month for cardmembers who make prompt payment for 12 consecutive months.) [ 63 20 1.1 ] 3 SHP
    0.5 NL
    F6
    (Tingkat 1 - Caj faedah 13.5% setahun pada bulan ke 13 bagi pemegang kad yang membuat bayaran pada atau sebelum tarikh bayaran matang bagi 12 bulan sebelumnya.) [ 63 20 1.1 ] 3 SHP

    % Insert notes for (b)
    01 NL
    F4
    (Tier 2 - 16.0% p.a. in interest charge on the 13th month for cardmembers who make prompt payment for either 10 or 11 months within the past 12 consecutive months.) [ 63 20 1.1 ] 3 SHP
    0.5 NL
    F6
    (Tingkat 2 - Caj faedah 16.0% setahun pada bulan ke 13 bagi pemegang kad yang membuat bayaran pada atau sebelum tarikh bayaran matang bagi 10 atau 11 bulan dalam kitaran 12 bulan.) [ 63 20 1.1 ] 3 SHP

    % Insert notes for (c)
    01 NL
    F4
    (Tier 3 - 17.5% p.a. in interest charge for cardmembers who do not meet the above criteria.) [ 63 20 1.1 ] 3 SHP
    0.5 NL
    F6
    (Tingkat 3 - Caj faedah 17.5% setahun bagi pemegang kad yang tidak memenuhi syarat di atas.) [ 63 20 01.1 ] 3 SHP

    45 95 MOVETO
    F4
    (18% p.a. on the cash advance/casino chips amount calculated on a daily basis from date of transaction.) [ 63 20 1.1 ] 3 SHP
    F6
    (18% setahun bagi amaun pendahuluan wang tunai/cip kasino dikira secara harian dari tarikh transaksi.) [ 63 20 1.1 ] 3 SHP

    % Insert paragraph 2
    01 NL
    F4
    (The cash advance fee is 5% of the amount advanced or a minimum of RM15, whichever is higher. This is imposed for each cash advance transaction.) [ 63 20 1.1 ] 3 SHP
    F6
    (Yuran bagi pendahuluan wang tunai ialah 5% dari jumlah pendahuluan wang tunai atau minima RM15, yang mana lebih tinggi. Ini dikenakan bagi setiap transaksi pendahuluan wang tunai.) [ 63 20 1.1 ] 3 SHP

    % Insert paragraph 3
    01 NL
    F4
    (5% of the outstanding balance or a minimum of RM50, whichever is higher.) [ 63 20 1.1 ] 3 SHP
    F6
    (5% dari baki tertunggak atau minima RM50, yang mana lebih tinggi.) [ 63 20 1.1 ] 3 SHP

    % Insert paragraph 4
    01 NL
    F4
    (The late payment charge is 1% of the outstanding balance due or RM5, whichever is higher, up to a maximum of RM50.) [ 63 20 1.1 ] 3 SHP
    F6
    (Caj Pembayaran Lewat ialah 1% dari baki tertunggak atau RM5, yang mana lebih tinggi, sehingga maksima RM50.) [ 63 20 1.1 ] 3 SHP

    % Insert paragraph 5
    01 NL
    F4
    (20 days from the statement date provided that there is no outstanding balance in the cardmember's account.) [ 63 20 1.1 ] 3 SHP
    (If the cardmember opts to make partial or minimum payment, finance charges on retail transactions will be imposed from the day the transaction is posted to the card account.) [ 63 20 1.1 ] 3 SHP
    F6
    (20 hari dari tarikh penyata dengan syarat tiada baki tertunggak di dalam akaun pemegang kad.) [ 63 20 1.1 ] 3 SHP
    (Jika pemegang kad membuat sebahagian atau bayaran minima, caj kewangan bagi urusniaga runcit akan dikenakan bermula dari tarikh transaksi  dibil ke dalam akaun kad.) [ 63 20 1.1 ] 3 SHP

    % Insert paragraph 6
    01 NL
    F4
    (Overseas transactions are subjected to the currency conversion rate determined by Visa International & MasterCard Worldwide plus a standard administration cost of 1% and any transaction fee charged by Visa International and MasterCard Worldwide.) [ 63 20 1.1 ] 3 SHP
    F6
    (Transaksi luar negara adalah tertakluk kepada kadar tukaran matawang yang ditentukan oleh Visa International & MasterCard Worldwide termasuk kos pentadbiran sebanyak 1% dan mana-mana caj transaksi oleh Visa International dan MasterCard Worldwide.) [ 63 20 1.1 ] 3 SHP

    % Insert paragraph 7
    F4
    45 178 MOVETO
    ((a)) SH

    6 NL
    ((b)) SH
    2.9 NL
    ((c)) SH
    2.9 NL
    ((d)) SH
    2.9 NL
    ((e)) SH

    F6
    45 197.6 MOVETO
    ((a)) SH

    6 NL
    ((b)) SH
    2.9 NL
    ((c)) SH
    2.9 NL
    ((d)) SH
    2.9 NL
    ((e)) SH

    % Insert English Versio
    50 178 MOVETO
    F4
    (i.  Current to 2 months - Free of Charge) [ 58 20 1.1 ] 3 SHP
    0.7 NL
    (ii.  Above 3 months - RM5 per statement)   [ 58 20 1.1 ] 3 SHP

    0.7 NL
    (RM25 per original copy and RM15 per duplicate copy) [ 58 20 1.2 ] 3 SHP
    0.7 NL
    (RM30 (Courier charge applicable for overseas delivery)) [ 58 20 1.2 ] 3 SHP
    0.7 NL
    (No charge) [ 58 20 1.2 ] 3 SHP
    0.7 NL
    (5% of total over limit amount or RM50, whichever is higher) [ 58 20 1.2 ] 3 SHP

    % Insert BM Version
    02.5 NL
    F6
    (i.   Terkini hingga 2 bulan - Percuma) [ 58 20 1.2 ] 3 SHP
    0.7 NL
    (ii.  3 bulan ke atas - RM5 bagi setiap penyata) [ 58 20 1.2 ] 3 SHP

    0.7 NL
    (RM25 setiap salinan asal dan RM15 setiap salinan pendua) [ 58 20 1.2 ] 3 SHP
    0.7 NL
    (RM30 (Caj kiriman dikenakan untuk penghantaran luar negara)) [ 58 20 1.2 ] 3 SHP
    0.7 NL
    (Tiada caj) [ 58 20 1.2 ] 3 SHP
    0.7 NL
    (5% dari jumlah amaun had lebih atau RM50, yang mana lebih tinggi.) [ 58 20 1.2 ] 3 SHP

    % Insert Examples Under Different Outstanding Amount Scenarios
    06 226 MOVETO
    (EUBX) SCALL

    06 225 MOVETO
    (**F5Table 1 / **F6Jadual 1) 0 SHmf

    57 228.5 MOVETO
    F5
    (Retail Purchase - Examples under different Outstanding Amount scenarios) VSUB SHc

    F6
    2.3 NL
    (Urusniaga Runcit - Contoh bagi senario-senario Baki Belum Jelas yang berbeza) VSUB SHc

    % Insert Outstanding Balance
    7.5  234.5 MOVETO
    F4
    (**F4Outstanding Balance) [ 33 50 1.1 ] 3 SHP
    (**F6Baki Belum Jelas (RM)) [ 33 50 1.1 ] 3 SHP

    % Insert Repayment Period
    1.3 NL
    (**F4Repayment period (months)) [ 33 50 1.1 ] 3 SHP
    (**F6Tempoh pembayaran balik (bulan)) [ 33 50 1.2 ] 3 SHP

    % Insert Total Interest Incured
    1.5 NL
    (**F4Finance Charges (RM)) [ 33 50 1.1 ] 3 SHP
    (**F6Caj Kewangan (RM)) [ 33 50 1.1 ] 3 SHP

    % Insert Tier 1
    1.6 NL
    (**F4Tier 1 / **F6Tingkat 1) [ 40 50 1.2 ] 3 SHP
    1.5 NL
    (**F4Tier 2 / **F6Tingkat 2) [ 40 50 1.2 ] 3 SHP
    02 NL
    (**F4Tier 3 / **F6Tingkat 3) [ 40 50 1.2 ] 3 SHP

    % Insert Repayment Value
    48 236 MOVETO
    F4
    00    MOVEHR (500)     SHc
    11.5  MOVEHR (1,000)   SHc
    22.5  MOVEHR (1,500)   SHc
    34.7  MOVEHR (2,000)   SHc
    46.4  MOVEHR (5,000)   SHc
    57.2  MOVEHR (10,000)  SHc

    06 NL
    00    MOVEHR (11)      SHc
    11.5  MOVEHR (24)      SHc
    22.5  MOVEHR (35)      SHc
    34.7  MOVEHR (43)      SHc
    46.4  MOVEHR (68)      SHc
    57.2  MOVEHR (88)      SHc

    % Insert Tier 1 Table
    10.5 NL
    -12	   MOVEHR (13.5% p.a.)      SHc
    00    MOVEHR (27.18)      SHc
    11.5  MOVEHR (124.87)     SHc
    22.5  MOVEHR (260.77)     SHc
    34.7  MOVEHR (396.66)     SHc
    46.4  MOVEHR (1,212.28)   SHc
    57.2  MOVEHR (2,571.50)   SHc

    % Insert Tier 2 Table
    03.5 NL
    -12	   MOVEHR (16.0% p.a.)      SHc
    00    MOVEHR (32.63)      SHc
    11.5  MOVEHR (152.77)     SHc
    22.5  MOVEHR (322.33)     SHc
    34.7  MOVEHR (491.93)     SHc
    46.4  MOVEHR (1,509.45)   SHc
    57.2  MOVEHR (3,205.30)   SHc

    % Insert Tier 3 Table
    04.5 NL
    -12	   MOVEHR (17.5% p.a.)      SHc
    00    MOVEHR (35.97)      SHc
    11.5  MOVEHR (170.57)     SHc
    22.5  MOVEHR (362.15)     SHc
    34.7  MOVEHR (553.66)     SHc
    46.4  MOVEHR (1,703.10)   SHc
    57.2  MOVEHR (3,618.89)   SHc

    % Insert In the event that
    07 266 MOVETO
    (**F5Change of Address Notification / **F6Pemberitahuan Pertukaran Alamat) 0 SHmf

    F4
    03 NL
    (Kindly call us at 1300-88-5000 or 03-8317 5000 to update your new address and contact number.) [ 103 20 1.1 ] 3 SHP

    F6
    0.5 NL
    (Hubungi kami di 1300-88-5000 atau 03-8317 5000 untuk mengemaskini alamat dan nombor telefon baru anda.) [ 103 20 1.1 ] 3 SHP

    01.5 NL
    F4
    (In the event that there be any conflict or discrepancy between information printed in English and Bahasa Malaysia, the English version shall prevail.) [ 103 20 1.3 ] 3 SHP

    0.5 NL
    F6
    (Sekiranya ada pertikaian atau percanggahan di antara maklumat yang dicetak dalam Bahasa Inggeris dan Bahasa Malaysia, versi Bahasa Inggeris akan diterima pakai.) [ 103 20 1.3 ] 3 SHP

    % Insert How to verify your statement text
    02.23 SETLSP
    114 22 MOVETO
    (**F5How To Verify Your Statement / **F6Bagaimana Mengesahkan Penyata Anda) 0 SHMF
    F4
    0.8 NL
    (Please examine this statement immediately by matching your copy of the transaction receipts to each of the itemised transactions. Any error therein must be reported to Credit Cards Department, OCBC Bank within 14 days from the date of the statement, failing which the statement shall be considered correct. The Bank shall investigate such complaint/dispute and respond within 30 days after officially lodged. You may bring the dispute to the Financial Mediation Bureau if you are not satisfied with the outcome of the investigation. For unstatemented transactions or to view your statement, please log on to our Internet Banking at **U0https://www.ocbc.com.my/internet-banking/**N0) 90 3 SHP

    01 NL
    F6
    (Sila periksa penyata ini segera dengan memadankan salinan resit transaksi anda dengan setiap butiran transaksi. Sebarang pertikaian hendaklah dilaporkan ke Bahagian Kad Kredit, OCBC Bank dalam masa 14 hari dari tarikh penyata, di mana penyata akan dianggap betul jika tiada laporan. Bank akan menjalankan siasatan ke atas rungutan/pertikaian dan akan memberi jawapan dalam masa 30 hari selepas dilaporkan. Anda boleh merujuk sebarang pertikaian ke Financial Mediation Bureau jika anda tidak berpuas hati dengan hasil penyiasatan. Untuk transaksi yang belum direkodkan atau untuk melihat penyata anda, sila daftar masuk ke Perbankan Internet di **U0https://www.ocbc.com.my/internet-banking/**N0) 90 3 SHP

    % Insert How to settle this account text
    02 NL
    (**F5How To Settle This Account / **F6Bagaimana Menyelesaikan Akaun Ini) 0 SHMF
    0.8 NL
    F4
    (You may choose to pay Minimum Payment or Total Balance in your monthly statement. The current due is 5% of the New Balance or RM50.00 whichever is greater. Should the new balance exceeds the Line of Credit, the due will be the entire amount in excess plus 5% of the Line of Credit. If the current due is not received in full two consecutive months, the whole minimum sum will become due and payable in the third month.) 90 3 SHP

    01 NL
    F6
    (Anda boleh memilih untuk membayar bayaran minima atau jumlah baki di dalam penyata bulanan anda. Baki tertunggak ialah 5% dari baki baru atau RM50, yang mana lebih tinggi. Jika baki baru melebihi jumlah kredit, baki tertunggak adalah keseluruhan lebihan jumlah  termasuk 5% jumlah kredit. Jika baki tertunggak tidak diterima dalam masa 2 bulan, keseluruhan jumlah minima akan menjadi tertunggak dan perlu dibayar di bulan ketiga.) 90 3 SHP

    % Insert What charges are levied?
    01 NL
    F4
    (After determining the Balances and the respective Periods on which the interest may be imposed, the following formula for the computation of interest is applicable:) 90 3 SHP
    0.5 NL
    (   A = (B) x (C/D) x (E) and F = Sum [A] where) 90 3 SHP

    118 92.5 MOVETO
    (   A = the interest charge for a particular balance "B" computed over the period of "C" days) 85  3 SHP

    0.5 NL
    (   B = the Balance that is imposed with interest) 85 3 SHP

    0.5 NL
    (   C = **FAthe respective interest bearing period in days on which the Balance "B" is imposed with interest**F4) 84.5 3 SHP
    0.5 NL
    (   D = the number of days used as the base for the annual rate) 85 3 SHP
    0.5 NL
    (   E = the nominal interest annual rate stated) 85 3 SHP
    0.5 NL
    (   F = the total interest imposed for the month) 85 3 SHP

    114 109 MOVETO
    F6
    (Selepas baki dan tempoh di mana faedah akan dikenakan telah ditentukan, formula bagi pengiraan faedah seperti dibawah digunakan:) 90 3 SHP
    0.8 NL
    (   A = (B) x (C/D) x (E) dan F = Jumlah [A] di mana) 90 3 SHP

    118 116.8 MOVETO
    (   A = kadar faedah bagi baki "B" dikira atas tempoh hari "C") 85 3 SHP

    0.5 NL
    (   B = baki yang dikenakan faedah) 85 3 SHP

    0.5 NL
    (   C = tempoh pengenaan faedah masing - masing mengikut hari di mana Baki "B" dikenakan faedah) 85 3 SHP
    0.5 NL
    (   D = jumlah hari digunakan sebagai asas kadar tahunan) 85 3 SHP
    0.5 NL
    (   E = kadar tahunan caj faedah ternyata) 85 3 SHP
    0.5 NL
    (   F = jumlah faedah yang dikenakan bagi bulan tersebut) 85 3 SHP

    % Insert How and where to make payment
    114 134 MOVETO
    (**F5How And Where To Make Payment / **F6Bagaimana Dan Di mana Membuat Pembayaran) 90 3 SHP

    0.7 NL
    F4
    (You can make payment in any of the following ways:) 90 3 SHP

    % Bullet for English version
    0.4  NL
    Z <75> SH 60 MOVEHR
    4.78 NL
    Z <75> SH 60 MOVEHR
    2.6  NL
    Z <75> SH 60 MOVEHR
    2.6  NL
    Z <75> SH 60 MOVEHR
    2.8  NL
    Z <75> SH 60 MOVEHR
    2.8  NL
    Z <75> SH 60 MOVEHR
    2.8  NL
    Z <75> SH 60 MOVEHR
    02.8 NL
    Z <75> SH 60 MOVEHR

    % Bullet for Malay version
    09.8 NL
    Z <75> SH 60 MOVEHR
    04.8   NL
    Z <75> SH 60 MOVEHR
    2.6  NL
    Z <75> SH 60 MOVEHR
    2.6  NL
    Z <75> SH 60 MOVEHR
    2.8  NL
    Z <75> SH 60 MOVEHR
    2.7  NL
    Z <75> SH 60 MOVEHR
    2.8  NL
    Z <75> SH 60 MOVEHR
    4.9  NL
    Z <75> SH 60 MOVEHR

    116.5 139.3 MOVETO
    F4
    (Mail your cheque directly to Credit Cards, OCBC Bank (Kindly indicate the name and relevant card number on the reverse of the cheque). Please do not mail cash.) 87.5 3 SHP
    0.5 NL
    (Deposit your cheque at the Deposit Cheque Machine at any OCBC branch in Malaysia.) 85 3 SHP
    0.5 NL
    (Deposit cash using the OCBC Cash-In ATMs.)  85 3 SHP
    0.5 NL
    (Make payments at OCBC ATMs by using the OCBC ATM card.)  85 3 SHP
    0.5 NL
    (Pay through OCBC Internet Banking at **U0https://www.ocbc.com.my/Internet-banking/**N0)  85 3 SHP
    0.5 NL
    (You can also make payments using the OCBC PhoneBank services.)  85 3 SHP
    0.5 NL
    (**FAUse InterBank Funds Transfer from your Current or Savings account at participating MEPS IBG banks.**F4)  85 3 SHP
    0.5 NL
    (Direct Debit Instruction may be effected on any current or savings account that you maintain at any OCBC Bank branch in Malaysia, to pay either minimum payment or new balance shown in your credit card statement without any additional charge.)  87.5 3 SHP

    114 167.8 MOVETO
    F6
    (Anda boleh membuat bayaran melalui:) 90 3 SHP

    116.5 170 MOVETO
    F6
    0.5 NL
    (Kirim cek ke Kad Kredit, OCBC Bank (Sila tulis nama dan nombor kad berkenaan di bahagian belakang cek). Hindari dari mengirim  wang tunai.) 87.5 3 SHP
    0.5 NL
    (Deposit cek anda melalui Mesin Deposit Cek di mana-mana cawangan OCBC Bank di Malaysia.) 85 3 SHP
    0.5 NL
    (Deposit wang tunai melalui Mesin Deposit Tunai OCBC.) 85 3 SHP
    0.5 NL
    (Mesin ATM OCBC dengan menggunakan Kad ATM OCBC.) 85 3 SHP
    0.5 NL
    (Perkhidmatan Perbankan Internet OCBC di **U0https://www.ocbc.com.my/Internet-banking/**N0) 85 3 SHP
    0.5 NL
    (Perkhidmatan Perbankan Telefon OCBC.) 85 3 SHP
    0.5 NL
    (Pemindahan Dana Antara Bank melalui akaun semasa/simpanan anda di bank-bank yang mengambil bahagian dalam rangkaian MEPS IBG.) 87.5 3 SHP
    0.5 NL
    (Arahan Tetap Debit Langsung melalui mana-mana akaun semasa atau simpanan anda di mana-mana cawangan OCBC Bank di Malaysia, samada bagi pembayaran minima atau baki tertunggak baru yang ditunjukkan di dalam penyata kad kredit anda tanpa apa-apa caj.) 87.5 3 SHP

    % Insert How transaction Made Outside Malaysia
    114 202 MOVETO
    (**F0How Transactions Made Outside Malaysia Are Processed/**F6Bagaimana Transaksi Luar Negara Diproses) 90 3 SHP
    0.8 NL
    F4
    (Transactions made outside Malaysia are converted to US Dollars before clearance through Visa International/MasterCard Worldwide. The US Dollars are reconverted to Ringgit Malaysia equivalent on Visa International/MasterCard Worldwide's processing date.) 90 3 SHP
    01 NL
    F6
    (Transaksi luar Malaysia akan ditukarkan ke Dolar Amerika Syarikat sebelum diluluskan melalui Visa International/MasterCard Worldwide. Dolar Amerika Syarikat kemudiannya akan ditukarkan ke Ringgit Malaysia bersamaan kadar pada tarikh proses Visa International/MasterCard Worldwide.) 90 3 SHP

    % Insert Where to report lost card
    02 NL
    (**F5Where To Report A Lost Or Stolen Card / **F6Melaporkan Kehilangan Atau Kecurian Kad) 90 3 SHP
    0.8 NL
    F4
    (In the event that the Credit Card is lost or stolen, report it immediately to Customer Service Executives at **F51-300-88-5000 or 03-8317 5000 (if calling from overseas)**F4. Select your preferred language and press "0" to speak to our Customer Service Executives. If you are overseas, kindly report to the nearest Visa/MasterCard member bank. The limited liability to Cardmember is RM250 (on charge that may have incurred) when you report the loss or stolen card immediately.) 90 3 SHP
    01 NL
    F6
    (Jika Kad Kredit hilang atau dicuri, laporkan segera ke Eksekutif Khidmat Pelanggan di **F71300-88-5000 atau 03-8317 5000 (bagi panggilan dari luar negara)**F6. Pilih jenis bahasa dan tekan "0" untuk bercakap dengan Eksekutif Khidmat Pelanggan kami. Jika anda berada di luar negara, sila laporkan ke mana-mana bank dalam rangkaian Visa/MasterCard. Liabiliti terhad kepada pemegang kad ialah RM250 (bagi caj yang mungkin terpakai) apabila anda melaporkan kehilangan atau kecurian kad dengan segera.) 90 3 SHP

    % Insert Enquiries
    02 NL
    (**F5Enquiries / **F6Pertanyaan) 90 3 SHP
    0.8 NL
    F4
    (If you have a query, please feel free to contact us at 1300-88-5000 or 03-8317 5000 (if calling from overseas) or mail to us at Cards & Unsecured Lending Department, OCBC Bank (Malaysia) Berhad, P.O. Box 10418, 50712 Kuala Lumpur or visit our website at **U0www.ocbc.com.**N0) 90 3 SHP

    01 NL
    (If you wish to seek alternative views to those of the Bank, you may contact the Financial Mediation Bureau at 03-2272 2811, email: **U0enquiry@fmb.org.my**N0; or Bank Negara Malaysia at 1300-88-LINK (5465), email: **U0bnmtelelink@bnm.gov.my**N0) 90 3 SHP
    01.5 NL
    F6
    (Jika anda mempunyai sebarang pertanyaan, sila hubungi kami di 1300-88-5000 atau 03-8317 5000 (bagi panggilan dari luar negara) atau tulis kepada kami di Cards & Unsecured Lending Department, OCBC Bank (Malaysia) Berhad, Beg Berkunci 10418, 50712 Kuala Lumpur atau layari halaman web kami di **U0www.ocbc.com.**N0) 90 3 SHP
    01 NL
    (Jika anda inginkan pandangan alternatif selain dari Bank, anda boleh hubungi Financial Mediation Bureau di 03-2272 2811, email: **U0enquiry@fmb.org.my**N0; atau Bank Negara Malaysia di 1300-88-LINK (5465), email: **U0bnmtelelink@bnm.gov.my**N0) 90 3 SHP

}  FSHOW
%%EOF
