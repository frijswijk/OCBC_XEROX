%!
%%Title: CASIOB.FRM
%%Creator: Lian 
%%CreationDate: Mon Jun 15 2009, 14:28:30.
%%EndComments

{  %%Begin Form
XGF
MM SETUNIT
ORITL
PORT
1.5 SETLSP

% Define Font Indexing
(//) 3 SETFTSW
/F1  /ARIALB  12  INDEXFONT
/F2  /ARIALB  07  INDEXFONT
/F3  /ARIAL   06  INDEXFONT


/F4  /ARIALB   09  INDEXFONT
/F5  /ARIALBO  07  INDEXFONT
/F6  /ARIAL    07  INDEXFONT
/F7  /ARIALB   08  INDEXFONT
/F8  /ARIALO   07  INDEXFONT
/F9  /ARIALBO  08  INDEXFONT

% Define Color Indexing
/B    BLACK        INDEXCOLOR
/R    RED          INDEXCOLOR

% Insert Company Name
F2
% 204.1  14 MOVETO (OCBC Bank (M) Berhad) SHR
% 20210427
 202.5 05 MOVETO (OCBC Bank (Malaysia) Berhad) SHR
 
NL F2
% F2
% ((295400-W)) SHR
% 20210427
 (199401009721 (295400-W)) SHR

% Insert URL text
F6 B 
02 SETLSP
%128 290 MOVETO (Your banking questions ANSWERED! For more info,) SHC
% R  01 NL  (log on to http://www.bankinginfo.com.my) SHC

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



}  FSHOW
%%EOF
