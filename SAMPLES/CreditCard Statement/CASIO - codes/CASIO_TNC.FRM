%!
%%Title: CASIO_TNC.FRM
%%Creator: Lian 
%%CreationDate: Mon Apr 27 2021, 14:28:30.
%%EndComments

{  %%Begin Form
XGF
MM SETUNIT
ORITL
PORT
2 SETLSP

% Define Font Indexing
(~~) 2 SETFTSW
/F1  /ARIALB   07  INDEXFONT
/F2  /ARIAL    06  INDEXFONT
/F3  /ARIAL    08  INDEXFONT
/F4  /ARIALB   09  INDEXFONT
/F5  /ARIALBO  07  INDEXFONT
/F6  /ARIAL    07  INDEXFONT
/F7  /ARIALB   08  INDEXFONT
/F8  /ARIALO   07  INDEXFONT
/F9  /ARIALBO  08  INDEXFONT
/F0  /ARIALO   08  INDEXFONT
/FI  /ARIALB   13  INDEXFONT
/FJ  /ARIAL    09  INDEXFONT
/FK  /ARIAL    05  INDEXFONT
/FL  /ARIALO   06  INDEXFONT
/FM  /ARIALB   06  INDEXFONT
/FZ  /NZDB     04  INDEXFONT

% Define Color Indexing
/B    BLACK        INDEXCOLOR
/R    RED          INDEXCOLOR

% Define BatKey Indexing
% ------------------------------------------------
/U0 	/UNDL 			  INDEXBAT
/N0 	 null 			  INDEXBAT
/P1 	/SUP			  INDEXSST
/P0 	 null 			  INDEXSST

/P2 [.15 .8] INDEXSST

% HEADER
% Insert Company Logo
%140.5 02 MOVETO
%(OCBC-LOGO.TIF) 0.08 0 ICALL
%(OCBC-LOGO-F.jpg) 0.024 0 ICALL
% June 2023
%145 02 MOVETO (OCBC.JPG)  0.2  0 ICALL
148 09 MOVETO (OCBC.eps) CACHE 0.18  SCALL

202.5 07 MOVETO F1 (199401009721 (295400-W)) SHR

% insert important notes
  09 09 MOVETO
  F7 (Important Notes For Cardmembers / Maklumat Penting Bagi Ahli Kad)  SH

% draw frame
%  08 12 193 268 S1 DRAWB

% insert table rows
	  09 10 MOVETO 2.75 SETLSP

	  % default table settings
	  [ /CellStroke [null null S1 S1] /Align 20 /Margins [0.8 0 1.5 1.5] /TextAtt {F6} ] BEGINTABLE
	  
      % covenient payment methods % how to verify your statement
	  [ [ /CellStroke S1 /TextAtt {F6} ]  % row defaults                  
	    [ /Width 194  /Align 23 /CellText (~~F1Convenient Payment Methods ~~F6: (a) Pay through OCBC Internet Banking. (b) Pay through OCBC mobile banking. (c) Use InterBank Funds Transfer from your Current or Savings account at participating MEPS IBG banks. (d) Direct Debit Instruction to directly debit your deposit account. (e) Pay through OCBC Auto Teller Machines (ATMs). (f) Pay through OCBC Phone Banking services. (g) Deposit Cash or Cheque through Cash Deposit Machine or Cheque Deposit Machine at any OCBC branch in Malaysia./~~F5Kaedah Pembayaran Yang Mudah ~~F8: (a) Bayar melalui Perkhidmatan Perbankan Internet OCBC. (b) Bayar melalui Perkhidmatan Perbankan Aplikasi Mobil OCBC. (c) Pemindahan Dana Antara Bank melalui akaun Semasa / Simpanan anda di bank-bank yang mengambil bahagian dalam rangkaian MEPS IBG. (d) Arahan Tetap Debit Langsung untuk mendebit terus daripada akaun deposit anda. (e) Bayar melalui Mesin ATM OCBC. (f) Bayar melalui Perkhidmatan Perbankan Telefon OCBC. (g) Deposit Wang Tunai atau Cek melalui Mesin Deposit Tunai atau Mesin Deposit Cek di mana-mana cawangan OCBC di Malaysia. \n~~F1How To Verify Your Statement ~~F6- Please examine your statement and inform Bank of any errors within 14 days from the statement date. In the absence of such notification, the statement of Credit Card account shall be deemed conclusive evidence of your confirmation and acceptance of the transaction therein. ~~F5Bagaimana untuk Mengesahkan Penyata Anda ~~F8- Sila periksa penyata anda dan beritahu Bank sekiranya terdapat sebarang kesilapan dalam tempoh 14 hari dari Tarikh Penyata, sekiranya anda gagal memberitahu Bank, maka Penyata Akaun Kad Kredit hendaklah dianggap sebagai bukti muktamad bahawa anda mengesah dan menerima transaksi yang dinyatakan di dalam Penyata tersebut.) ]                      
	  ] SHROW

      % payment allocation statement                  
	  [ [ /CellStroke S1 /TextAtt {F6} ]  % row defaults
	  	[ /Width 194  /Align 23 /CellText (~~F1Payment Allocation Statement ~~F6- Payment received from cardmembers will be allocated to settle balances (items appearing in the statement) attracting the highest interest first. ~~F5Penyata Peruntukan Pembayaran ~~F8- Pembayaran yang diterima daripada ahli kad akan diperuntukkan untuk menyelesaikan baki (butiran yang terdapat dalam penyata) yang menarik kadar faedah yang tertinggi terdahulu.) ]    
	  ] SHROW

      % finance charges                  
	  [ [ /CellStroke [null null S1 S1] /TextAtt {F6} ]  % row defaults
	  	[ /Width 194  /Align 23 /CellText (~~P2~~FZl~~P0 ~~F1Finance Charges - (a) Retail Purchases including Balance Transfer & Call-for-Cash ~~F6- (i) Tier 1: 15% p.a. in interest charge for cardmembers who make prompt payment for 12 consecutive months. (ii) Tier 2: 17% p.a. in interest charge for cardmembers who make prompt payment for either 10 or 11 months within the past 12 consecutive months. (iii) Tier 3: 18% p.a. in interest charge for cardmembers who do not meet the above criteria. To enjoy lower finance charges for retail transactions, you should make at least 10 prompt payments in the last 12 months. ~~F1(b) Cash Advance / Casino Chips ~~F6- 18% p.a. of the Cash Advance / Casino Chips amount calculated on a daily basis from the date of transaction./~~F5Caj Kewangan - (a) Urus Niaga Runcit termasuk Pemindaan Baki & Call-for-Cash ~~F8- (i) Tingkat 1: 15% setahun bagi ahli kad dengan pembayaran tepat selama 12 bulan berturut-turut. (ii) Tingkat 2: 17% setahun bagi ahli kad dengan pembayaran tepat bagi 10 atau 11 bulan dalam 12 bulan yang lepas. (iii) Tingkat 3: 18% setahun bagi ahli kad yang tidak memenuhi kriteria di atas. Untuk menikmati caj kewangan yang lebih rendah bagi urus niaga runcit, anda perlu membuat sekurang-kurangnya 10 pembayaran tepat dalam kitaran 12 bulan. ~~F5(b) Pendahuluan Wang Tunai / Cip Kasino ~~F8- 18% setahun atas amaun Pendahuluan Wang Tunai / Cip Kasino dikira secara harian dari tarikh urus niaga.) ]
	  ] SHROW

	  % balance transfer interest charge  
	  [	[ /CellStroke [null null S1 S1] /Margins [0.5 0 1.5 1.5] /TextAtt {F6} ]  % row defaults
	  	[ /Width 194  /Align 23 /CellText (~~P2~~FZl~~P0 ~~F1Balance Transfer Interest Charge ~~F6- 6% p.a. flat or lower due to promotional interest rate / ~~F5Caj Faedah Pemindahan Baki ~~F8- Kadar faedah rata 6% setahun atau lebih rendah bagi kadar faedah promosi.) ]                        
	  ] SHROW

      % call for cash                  
	  [	[ /CellStroke [null null S1 S1] /Margins [0.5 0 1.5 1.5] /TextAtt {F6} ]  % row defaults
	  	[ /Width 194  /Align 23 /CellText (~~P2~~FZl~~P0 ~~F1Call-for-Cash (CFC) ~~F6-  (a) Interest Rate - 9% p.a. flat or lower due to promotional interest rate (b) Cash Advance Fee - 3% or lower due to promotional interest rate (one-time fee) / ~~F8(a) Kadar Faedah - Rata 9% setahun atau lebih rendah bagi kadar faedah promosi (b) Yuran Pendahuluan Tunai - 3% atau lebih rendah bagi kadar faedah promosi (yuran satu kali).) ]                        
	  ] SHROW

      % cash advance / casino chips fees                  
	  [	[ /CellStroke [null null S1 S1] /Margins [0.5 0 1.5 1.5] /TextAtt {F6} ]  % row defaults
	  	[ /Width 194  /Align 23 /CellText (~~P2~~FZl~~P0 ~~F1Cash Advance / Casino Chips Fees ~~F6- 5% of the amount advanced or a minimum of RM20, whichever is higher. This is imposed for each cash advance transaction./ ~~F5Yuran Pendahuluan Tunai / Cip Kasino ~~F8- 5% daripada amaun pendahuluan atau minima RM20, yang mana lebih tinggi. Yuran ini dikenakan bagi setiap urus niaga pendahuluan tunai.) ]                        
	  ] SHROW

      % late payment charge                   
	  [	[ /CellStroke [null null S1 S1] /Margins [0.5 0 1.5 1.5] /TextAtt {F6} ]  % row defaults
	  	[ /Width 194  /Align 23 /CellText (~~P2~~FZl~~P0 ~~F1Late Payment Charge ~~F6- 1% late payment fee only applicable to retail transactions and cash advance or RM10 (whichever is higher), subject to a maximum of RM100 / ~~F5Yuran Pembayaran Lewat ~~F8- 1% yuran pembayaran lewat hanya untuk transaksi runcit dan pendahuluan tunai atau RM10 (yang mana lebih tinggi), tertakluk kepada maksimum RM100.) ]                        
	  ] SHROW

      % conversion for overseas transactions                   
	  [	[ /CellStroke [null null S1 S1] /Margins [0.5 0 1.5 1.5] /TextAtt {F6} ]  % row defaults
	  	[ /Width 194  /Align 23 /CellText (~~P2~~FZl~~P0 ~~F1Conversion for Overseas Transactions ~~F6- Overseas Transactions are subject to the currency conversion rate determined by Visa International and Mastercard Worldwide plus a standard administration cost of 1.00% for OCBC 365 Mastercard and 1.25%** for all other cards and any transaction fee charged by Visa International and Mastercard Worldwide./ ~~F5Penukaran untuk Urus Niaga Luar Negera ~~F8- Urus niaga luar negara adalah tertakluk kepada kadar tukaran matawang yang ditentukan oleh Visa International dan Mastercard Worldwide termasuk yuran pentadbiran sebanyak 1.00% untuk OCBC 365 Mastercard dan 1.25%** untuk semua kad lain dan mana-mana yuran urus niaga yang dikenakan oleh Visa International dan Mastercard Worldwide.) ]                        
	  ] SHROW

      % monthly statement retrieval fee                   
	  [	[ /CellStroke [null null S1 S1] /Margins [0.5 0 1.5 1.5] /TextAtt {F6} ]  % row defaults
	  	[ /Width 194  /Align 23 /CellText (~~P2~~FZl~~P0 ~~F1Monthly Statement Retrieval Fee ~~F6- (i) Current to 2 months - Free of Charge. (ii) Above 3 months - RM5 per statement / ~~F5Yuran Pengeluaran Penyata Bulanan ~~F8- (i) Terkini hingga 2 bulan - Percuma. (ii) 3 bulan ke atas - RM5 bagi setiap penyata.) ]                        
	  ] SHROW

      % sales draft retrieval fee                   
	  [	[ /CellStroke [null null S1 S1] /Margins [0.5 0 1.5 1.5] /TextAtt {F6} ]  % row defaults
	  	[ /Width 194  /Align 23 /CellText (~~P2~~FZl~~P0 ~~F1Sales Draft Retrieval Fee ~~F6- RM15 per original copy. RM10 (all cards except OCBC 365 Mastercard & OCBC Premier Voyage Mastercard) and RM8 (OCBC 365 Mastercard & OCBC Premier Voyage Mastercard) per duplicate copy./ ~~F5Yuran Resit Urus Niaga ~~F8- RM15 setiap salinan asal. RM10 (semua kad kecuali OCBC 365 Mastercard & OCBC Premier Voyage Mastercard) dan RM8 (OCBC 365 Mastercard & OCBC Premier Voyage Mastercard) bagi setiap salinan pendua.) ]                        
	  ] SHROW	  

      % card replacement fee                   
	  [	[ /CellStroke [null null S1 S1] /Margins [0.5 0 1.5 1.5] /TextAtt {F6} ]  % row defaults
	  	[ /Width 194  /Align 23 /CellText (~~P2~~FZl~~P0 ~~F1Card Replacement Fee ~~F6- (i) RM50** (ii) RM35 for OCBC 365 Mastercard (iii) RM500 for OCBC Premier Voyage Mastercard / ~~F5Yuran Penggantian Kad ~~F8- (i) RM50** (ii) RM35 untuk OCBC 365 Mastercard. (iii) RM500 untuk OCBC Premier Voyage Mastercard.) ]                        
	  ] SHROW
	  
      % cheque returned fee / over limit fee                   
	  [	[ /CellStroke [null null S1 S1] /Margins [0.5 0 1.5 1.5] /TextAtt {F6} ]  % row defaults
	  	[ /Width 194  /Align 23 /CellText (~~P2~~FZl~~P0 ~~F1Cheque Returned Fee / Over Limit Fee ~~F6- No charge./ ~~F5Yuran Pemulangan Cek / Yuran Had Lebih ~~F8- Tiada caj.) ]                        
	  ] SHROW	  
	  	  
      % interest free period for retail purchases                   
	  [ [ /CellStroke S1 /Margins [0.5 0 1.5 1.5] /TextAtt {F6} ]  % row defaults
	  	[ /Width 194  /Align 23 /CellText (~~F1Interest Free Period for Retail Purchases ~~F6- 20 days from the statement date provided that there is no outstanding balance in the cardmember's account. If the cardmember opts to make partial or minimum payment, finance charges on retail transactions will be imposed from the day the transaction is posted to the card account. The following formula will apply for the computation of interest: ~~F1A = (B) x (C/D) x (E) and F = Sum [A]~~F6 where A = the interest charge for a particular balance "B" computed over the period of "C" days. B = the Balance that is imposed with interest. C = the respective interest bearing period in days on which the Balance "B" is imposed with interest. D = the number of days used as the base for the annual rate. E = the nominal interest annual rate stated. F = the total interest imposed for the month. The interest free period is not applicable to balance transfer or cash advances./~~F5Tempoh Bebas Faedah untuk Urus Niaga Runcit ~~F8- 20 hari dari tarikh penyata dengan syarat tidak terdapat baki belum jelas dalam akaun ahli kad. Jika ahli kad memilih untuk membuat pembayaran sebahagian atau minima, caj kewangan bagi urus niaga runcit akan dikenakan dari tarikh urus niaga dicatatkan pada akaun kad. Formula pengiraan faedah adalah seperti berikut: ~~F5A = (B) x (C/D) x (E) dan F = Jumlah [A]~~F8 di mana A = kadar faedah bagi baki "B" dikira atas tempoh hari "C". B = baki yang dikenakan faedah. C = tempoh pengenaan faedah masing-masing mengikut hari di mana Baki "B" dikenakan faedah. D = jumlah hari digunakan sebagai asas kadar tahunan. E = kadar tahunan caj faedah ternyata. F = jumlah faedah yang dikenakan bagi bulan tersebut. Tempoh tanpa faedah adalah tidak terpakai bagi Pendahuluan Tunai atau Pemindahan Baki.) ]                        
	  ] SHROW

      % minimum monthly repayment                   
	  [ [ /CellStroke S1 /TextAtt {F6} ]  % row defaults
	  	[ /Width 194  /Align 23 /CellText (~~F1Minimum Monthly Repayment ~~F6means the higher of ~~F7(a)~~F6 and ~~F7(b)~~F6: ~~F7(a)~~F6 The aggregate of the following; (i)  5% of the new balance* (excluding the contracted monthly instalment referred in (ii) below); AND (ii) 100% of all contracted monthly instalment amounts including for any instalment payment plans, balance transfer plans and any auto balance conversion ("ABC"). ~~F7(b)~~F6 RM50. For more information on what is ABC, who is eligible to qualify for ABC and how ABC works, please visit OCBC website. *As defined in OCBC Cardmember's Agreement / ~~F5Bayaran Minima Bulanan ~~F8bermaksud yang mana lebih tinggi diantara ~~F5(a)~~F8 dan ~~F5(b)~~F8: ~~F5(a)~~F8 Jumlah agregat untuk yang berikut; (i)  5% daripada baki baru* (tidak termasuk ansuran bulanan yang dikontrakkan seperti yang dirujuk  kepada (ii) di bawah); DAN (ii)  100% daripada ansuran bulanan yang dikontrakkan termasuk sebarang pelan bayaran ansuran bulanan, pelan pemindahan baki dan sebarang penukaran baki automatic ("Auto Balance Conversion"-ABC).  ~~F5(b)~~F8 RM50. Untuk maklumat lanjut berkenaan ABC, kelayakkan serta bagaimana ABC berfungsi, sila layari laman sesawang OCBC. \n* Sepertimana yang ditakrifkan dalam OCBC Perjanjian Ahli Kad.) ]                        
	  ] SHROW

      % liability for unauthorised transactions                   
	  [ [ /CellStroke S1 /TextAtt {F6} ]  % row defaults
	  	[ /Width 194  /Align 23 /CellText (~~F1Liability for Unauthorised Transactions ~~F6-You will bear the losses arising from your negligence in safeguarding your Credit Card from loss or theft or the PIN from being disclosed, or your failure to notify the OCBC's Credit Card Centre, immediately after finding that the Credit Card is lost or stolen or PIN is disclosed or if you suspect an unauthorised transaction had been conducted. You must make a police report and a copy of the report must be provided to the Bank. / ~~F5Liabiliti untuk Urus Niaga yang Tidak Dibenarkan ~~F8- Anda akan menanggung segala kerugian akibat kecuaian anda mengawasi Kad Kredit anda dari kehilangan, kecurian atau PIN terdedah, atau kegagalan anda melaporkan ke Pusat Kad Kredit OCBC, sebaik sahaja anda mengetahui akan kehilangan, kecurian, pendedahan. PIN ataupun anda mengesyaki Kad Kredit anda disalahgunakan. Anda perlu membuat laporan polis dan salinan laporan perlu diberikan kepada OCBC.) ]                        
	  ] SHROW

      % notice on paying only minimum monthly repayment                   
	  [	[ /CellStroke [null null S1 S1] /Margins [0.5 0 1.5 1.5] /TextAtt {F6} ]  % row defaults
	  	[ /Width 194  /Align 23 /CellText (~~F1Notice On Paying Only Minimum Monthly Repayment ~~F6- The table below illustrates how long it would take to pay off an outstanding balance and amount of interest incurred if you continue to pay only the minimum payment amount. The computations are based on 5% minimum payment of the monthly outstanding balance or RM50, whichever is higher, at a financial charge of 18% p.a. provided no new retail transactions. This calculation is based on 30 days a month. / ~~F5Notis Sekiranya Pelanggan Membuat Bayaran Minimum Bulanan Sahaja ~~F8- Jadual di bawah menggambarkan masa yang diambil untuk menjelaskan baki belum jelas dan jumlah faedah yang ditanggung jika anda hanya membuat bayaran minimum secara berterusan. Pengiraan adalah berasaskan bayaran minimum 5% baki bulanan tertunggak atau RM50, yang mana lebih tinggi, pada caj faedah 18% setahun selagi tiada transaksi baru. Pengiraan ini berdasarkan tempoh 30 hari sebulan.) ]                        
	  ] SHROW

      % table 1-outstanding balance (RM) / jadual 1-baki belum jelas (RM)                  
	  [ [ /CellStroke S1 /TextAtt {F2} ]  % row defaults
		[ /Width 02  /CellStroke [null null S1 null] ]
	  	[ /Width 40   /Align 23 /CellText (~~F1Table 1-Outstanding Balance / ~~F5 \nJadual 1-Baki Belum Jelas (RM)) ] 
	    [ /Width 50   /CellFill LMED /Margins [2 0 1.5 1.5] /Align 22 /CellText (~~F13,000) ]      
	    [ /Width 50   /CellFill LMED /Margins [2 0 1.5 1.5] /Align 22 /CellText (~~F15,000) ]  
	    [ /Width 50   /CellFill LMED /Margins [2 0 1.5 1.5] /Align 22 /CellText (~~F110,000) ]                    
		[ /Width 02   /CellFill null /CellStroke [null null null S1] ]
	  ] SHROW

	  % repayment / pembayaran balik
	  [ [ /CellStroke S1 /TextAtt {F2} ]  % row defaults
		[ /Width 02  /CellStroke [null null S1 null] ]
	  	[ /Width 40  /Align 23 /CellText (~~F6Repayment / ~~F8Pembayaran) ] 
	    [ /Width 25  /CellFill LMED /Align 22 /CellText (~~F6Pay only minimum amount in  1~~P1st~~P0 month / ~~F8Bayar minimum dalam bulan pertama~~F6 (RM150)) ]      
	    [ /Width 25  /CellFill LMED /Align 22 /CellText (~~F6Pay every month / ~~F8Bayar setiap bulan~~F6 (RM250)) ]  
	    [ /Width 25  /CellFill LMED /Align 22 /CellText (~~F6Pay only minimum amount in  1~~P1st~~P0 month / ~~F8Bayar minimum dalam bulan pertama~~F6 (RM250)) ]                    
	    [ /Width 25  /CellFill LMED /Align 22 /CellText (~~F6Pay every month / ~~F8 Bayar setiap bulan~~F6 (RM350)) ]  
	    [ /Width 25  /CellFill LMED /Align 22 /CellText (~~F6Pay only minimum amount in  1~~P1st~~P0 month / ~~F8Bayar minimum dalam bulan pertama~~F6 (RM500)) ]                    
	    [ /Width 25  /CellFill LMED /Align 22 /CellText (~~F6Pay every month / ~~F8 Bayar setiap bulan~~F6 (RM600)) ]  
		[ /Width 02  /CellFill null /CellStroke [null null null S1] ]
	  ] SHROW

      % repayment period (months) / tempoh pembayaran balik (bulan)                
	  [ [ /CellStroke S1 /TextAtt {F2} ]  % row defaults
		[ /Width 02  /CellStroke [null null S1 null] ]
	  	[ /Width 40  /Align 23 /CellText (~~F6Repayment Period (months) / ~~F8 Tempoh Pembayaran Balik (bulan)) ] 
	    [ /Width 25  /Align 22 /CellText (~~F64 years 7 months~~F8 \n4 tahun 7 bulan) ]      
	    [ /Width 25  /Align 22 /CellText (~~F61 year 2 months~~F8 \n1 tahun 2 bulan) ]  
	    [ /Width 25  /Align 22 /CellText (~~F65 years 9 months~~F8 \n5 tahun 9 bulan) ]                    
	    [ /Width 25  /Align 22 /CellText (~~F61 year 5 months~~F8 \n1 tahun 5 bulan) ]  
	    [ /Width 25  /Align 22 /CellText (~~F67 years 4 months~~F8 \n7 tahun 4 bulan) ]                    
	    [ /Width 25  /Align 22 /CellText (~~F61 year 8 months~~F8 \n1 tahun 8 bulan) ]  
		[ /Width 02  /CellStroke [null null null S1] ]
	  ] SHROW

      % total interest incurred (RM)/ jumlah faedah yang dikenakan (RM)                   
	  [ [ /CellStroke S1 /TextAtt {F2} ]  % row defaults
		[ /Width 02  /CellStroke [null null S1 null] ]
	  	[ /Width 40  /Align 23 /CellText (~~F6Total Interest Incurred / ~~F8Jumlah Faedah Yang Dikenakan (RM)) ] 
	    [ /Width 25  /Margins [2 0 1.5 1.5] /Align 22 /CellText (~~F61,055) ]      
	    [ /Width 25  /Margins [2 0 1.5 1.5] /Align 22 /CellText (~~F6333) ]  
	    [ /Width 25  /Margins [2 0 1.5 1.5] /Align 22 /CellText (~~F61,912) ]                    
	    [ /Width 25  /Margins [2 0 1.5 1.5] /Align 22 /CellText (~~F6670) ]  
	    [ /Width 25  /Margins [2 0 1.5 1.5] /Align 22 /CellText (~~F64,055) ]                    
	    [ /Width 25  /Margins [2 0 1.5 1.5] /Align 22 /CellText (~~F61,594) ]  
		[ /Width 02  /CellStroke [null null null S1] ]
	  ] SHROW

      % total amount to be settled / jumlah perlu dijelaskan (RM)                   
	  [ [ /CellStroke S1 /TextAtt {F6} ]  % row defaults
		[ /Width 02  /CellStroke [null null S1 null]]
	  	[ /Width 40  /Align 23 /CellText (~~F6Total Amount To Be Settled / ~~F8Jumlah Perlu Dijelaskan (RM)) ] 
	    [ /Width 25  /Margins [2 0 1.5 1.5] /Align 22 /CellText (~~F64,055) ]      
	    [ /Width 25  /Margins [2 0 1.5 1.5] /Align 22 /CellText (~~F63,333) ]  
	    [ /Width 25  /Margins [2 0 1.5 1.5] /Align 22 /CellText (~~F66,912) ]                    
	    [ /Width 25  /Margins [2 0 1.5 1.5] /Align 22 /CellText (~~F65,670) ]  
	    [ /Width 25  /Margins [2 0 1.5 1.5] /Align 22 /CellText (~~F614,055) ]                    
	    [ /Width 25  /Margins [2 0 1.5 1.5] /Align 22 /CellText (~~F611,594) ]  
		[ /Width 02  /CellStroke [null null null S1] ]
	  ] SHROW

      % enquiries                   
	  [	[ /CellStroke S1 /TextAtt {F6} ]  % row defaults
	  	[ /Width 194  /Align 23 /CellText (~~F1Enquiries ~~F6- For Lost / Stolen Card reporting, Change of Contact Details, Notification of Error or Disputes on Card Statement, Enquiries or Complaints, please contact us at 03-8317 5000 or mail to Consumer Lifestyle Finance Department, OCBC Bank (Malaysia) Berhad, P.O. Box 10418, 50712 Kuala Lumpur or visit OCBC website. If you wish to seek alternative views, you may contact Bank Negara Malaysia, BNM TELELINK at 1300-88-5465, web form: telelink.bnm.gov.my; or Ombudsman for Financial Services (OFS) at 03-2272 2811. / ~~F5Pertanyaan ~~F8- Untuk Laporan Kehilangan / Kecurian Card, Penukaran Maklumat Hubungan, Pemberitahuan mengenai Kesilapan atau Pertikaian mengenai Penyata Kad, Pertanyaan atau Aduan, sila hubungi kami di 03-8317 5000 atau tulis kepada kami di Consumer Lifestyle Finance Department, OCBC Bank (Malaysia) Berhad, Karung Berkunci 10418, 50712 Kuala Lumpur atau layari halaman web OCBC. Jika anda inginkan pandangan alternatif selain dari Bank, anda boleh hubungi Bank Negara Malaysia, BNM TELELINK di 1300-88-5465, borang web: telelink.bnm.gov.my atau Ombudsman Perkhidmatan Kewangan (OPK) di 03-2272 2811.) ]                        
	  ] SHROW

		
% FOOTER
% insert not applicablle for
%F6 09 283.5 MOVETO
F6 09 286.5 MOVETO
(~~F6** Not applicable to/~~F8tidak sah untuk ~~F6OCBC Premier Voyage Mastercard.) [ 196 20 1.3 ] 3 SHP

% Insert URL text
F6 B 
02 SETLSP
%128 290 MOVETO (Your banking questions ANSWERED! For more info,) SHC
%R  01 NL  (log on to http://www.bankinginfo.com.my) SHC

 % 20210427
 %  08 290 MOVETO (Your banking questions ANSWERED! For more info,) SHL
 %  R  01 NL (log on to http://www.bankinginfo.com.my) SHL

% Insert Group Name
F6 B
186.5 290 MOVETO
(A Member of OCBC Group) SHC

R 01 NL (https://www.ocbc.com.my) SHC B

 % 20210427
 %   201.5 290 MOVETO  (A Member of OCBC Group) SHR
 %	R  01 NL  (http://www.ocbc.com.my) SHR  B


}  % FSHOW
% EOF


