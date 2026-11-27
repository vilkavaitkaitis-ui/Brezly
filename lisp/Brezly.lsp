;;; ============================================================
;;;  Brezly.lsp - Brezly praktika tiesiai AutoCAD viduje
;;;  Versija 1.5.1
;;;
;;;  Idiegimas: nutempk si faila i AutoCAD langa
;;;  (arba APPLOAD -> pasirink Brezly.lsp -> Load).
;;;  Kad kraututusi kas kart: APPLOAD -> Startup Suite -> Add.
;;;
;;;  Komandos:
;;;    BREZLY   - atidaro praktikos langa
;;;    TIKRINK  - patikrina dabartine uzduoti
;;;    BRLAPAS  - nubraizo lapo remeli su spaudu
;;; ============================================================

(setq *br:ver* "1.5.1")

;;; Uzduotis: (id pav fmt d min xp aprasas komandos zingsniai taisykles)
;;; Taisykles: ("R" spindulys kiek) ("T" tipas kiek) ("DYDIS" plotis aukstis) ("TURIS" mm3 proc)
;;; <uzduotys> - GENERUOJAMA is praktika/uzduotys.json (python irankiai/generuoti.py), ranka nekeisti
(setq *br:uzd*
 (list
  (list "U1_Tarpine" "Tarpine" "A4" "2D" 10 30
   "Nubraizyk tarpine 120 x 80 su uzapvalintais kampais R10, centrine skyle D40 ir keturiomis skylemis D10."
   "RECTANG, FILLET, CIRCLE, COPY, DIMLINEAR"
   (list "RECTANG -> Fillet -> R10, tada staciakampis 120,80"
         "CIRCLE centre -> spindulys 20 (D40)"
         "Viena skyle: CIRCLE spindulys 5, tada COPY i kitus 3 kampus (atstumai 96 ir 56)"
         "Asys sluoksnyje ASYS, matmenys - DIMLINEAR")
   (list (list "R" 20.0 1) (list "R" 5.0 4) (list "T" "LINE" 4) (list "T" "ARC" 4) (list "DYDIS" 120.0 80.0)))

  (list "U2_Flansas" "Flansas" "A4" "2D" 15 45
   "Flansas D120 su anga D50 ir 6 skylemis D12 ant D90 apskritimo. Du vaizdai: is virsaus ir is priekio."
   "CIRCLE, ARRAY (Polar), LINE, NEMATOMOS, DIMDIAMETER"
   (list "Trys koncentriniai apskritimai: R60, R25 ir R45 (asinis, sluoksnis ASYS)"
         "Viena skyle R6 ant asinio apskritimo virsaus"
         "ARRAYPOLAR -> 6 elementai, 360 laipsniu"
         "Vaizdas is priekio: staciakampis 120 x 15, skyles - bruksnines (NEMATOMOS)")
   (list (list "R" 60.0 1) (list "R" 25.0 1) (list "R" 6.0 6)))

  (list "U3_Laikiklis" "L laikiklis" "A4" "2D" 15 45
   "L formos laikiklis 100 x 80 su vidiniu kampu R10, skyle D12 ir ovalia anga 30 x 10."
   "PLINE, FILLET, CIRCLE, OFFSET, TRIM"
   (list "PLINE konturas pagal matmenis (100, 30, 70, 50, 30, 80)"
         "FILLET R10 vidiniame kampe"
         "Skyle: CIRCLE R6 per 15 nuo krasto ir 20 nuo virsaus"
         "Ovalas: du apskritimai R5 per 20 vienas nuo kito + dvi liestines LINE, TRIM viduri")
   (list (list "R" 6.0 1) (list "T" "ARC" 3)))

  (list "U4_Velenas" "Velenas" "A4" "2D" 15 50
   "Pakopinis velenas D20 / D30 / D25 (ilgiai 30, 50, 40) su grioveliu 30 x 8 ir pjuviu A-A."
   "LINE, OFFSET, CHAMFER, MIRROR, HATCH"
   (list "Nubraizyk tik virsutine puse nuo asies, tada MIRROR per asi"
         "CHAMFER 1 x 45 laipsniu galuose"
         "Griovelis: staciakampis su uzapvalintais galais 30 x 8"
         "Pjuvis A-A: apskritimas D30 su ipjova, uzpildyk HATCH (ANSI31)")
   (list (list "T" "LINE" 14) (list "T" "HATCH" 1)))

  (list "U5_Projekcijos" "3 projekcijos" "A4" "2D" 20 60
   "L formos blokas 60 x 40 x 40 su laipteliu ir kiaurine skyle D14. Trys vaizdai E metodu."
   "LINE, XLINE, CIRCLE, NEMATOMOS, DIMLINEAR"
   (list "Pradek nuo vaizdo is priekio (60 x 40 su laipteliu 30 x 20)"
         "XLINE pagalbinemis linijomis perkelk aukscius i vaizda is kaires (desineje)"
         "Vaizdas is virsaus - apacioje: 60 x 40, skyle R7"
         "Nematomos skyles briaunos - sluoksnis NEMATOMOS")
   (list (list "R" 7.0 1) (list "T" "LINE" 14)))

  (list "U6_Izometrija" "Izometrija" "A3" "3D" 20 60
   "5 uzduoties detale nubraizyk izometrijoje masteliu 2:1. Skyle - izometrinis apskritimas."
   "ISODRAFT, F5, LINE, ELLIPSE -> Isocircle, COPY"
   (list "Ijunk ISODRAFT (arba busenos juostoje izometrini tinkleli)"
         "F5 keicia plokstuma: kaire / virsus / desine"
         "Matmenys x2: 120, 80, 80, laiptelis 40"
         "Skyle: ELLIPSE -> I (Isocircle), spindulys 14, virsutineje plokstumoje")
   (list (list "T" "LINE" 12) (list "T" "ELLIPSE" 1)))

  (list "U7_Schema" "Elektrine schema" "A4" "2D" 15 45
   "Schema: baterija G1, jungiklis S1, rezistorius R1 ir dvi lygiagrecios lemputes H1, H2 + apraso lentele."
   "BLOCK, ATTDEF, INSERT, LINE, TABLE"
   (list "Nubraizyk zenklus (lempute - apskritimas su X, rezistorius 15 x 5)"
         "Kiekviena paversk bloku: BLOCK, su atributu POZ (ATTDEF)"
         "INSERT - sudek blokus ir sujunk linijomis"
         "Apraso lentele - TABLE arba linijos + tekstas")
   (list (list "T" "INSERT" 4) (list "T" "LINE" 6)))

  (list "U8_3D_detale" "3D detale" "A3" "3D" 25 80
   "Plokste 80 x 50 x 10 su cilindru D30 (aukstis iki 35), kiaurine skyle D16 ir 4 skylemis D8."
   "BOX, CYLINDER, UNION, SUBTRACT, ARRAY, VIEWBASE"
   (list "BOX nuo 0,0,0 -> 80,50,10"
         "CYLINDER centras 40,25,10, R15, aukstis 25 -> UNION su plokste"
         "CYLINDER R8 kiaurai visa auksti ir 4 x R4 (10 nuo krastu) -> SUBTRACT"
         "Patikrink: MASSPROP -> turis apie 48 600 mm3")
   (list (list "T" "3DSOLID" 1) (list "TURIS" 48623.7 2.0)))
 ))
;;; </uzduotys>

;;; ---------- pagalbines ----------

(defun br:u (i) (nth i *br:uzd*))

(defun br:fmt (x)
  (if (equal x (fix (+ x 0.5)) 0.001)
    (itoa (fix (+ x 0.5)))
    (rtos x 2 2)))

(defun br:skaidyti (s plotis / zodziai z i c eil r)
  (setq zodziai nil z "" i 1)
  (while (<= i (strlen s))
    (setq c (substr s i 1))
    (if (= c " ")
      (progn (if (/= z "") (setq zodziai (cons z zodziai))) (setq z ""))
      (setq z (strcat z c)))
    (setq i (1+ i)))
  (if (/= z "") (setq zodziai (cons z zodziai)))
  (setq zodziai (reverse zodziai) eil "" r nil)
  (foreach z zodziai
    (if (and (/= eil "") (> (+ (strlen eil) 1 (strlen z)) plotis))
      (setq r (cons eil r) eil z)
      (setq eil (if (= eil "") z (strcat eil " " z)))))
  (if (/= eil "") (setq r (cons eil r)))
  (reverse r))

;;; ---------- progresas ----------

(defun br:kelias (/ d)
  (setq d (getenv "USERPROFILE"))
  (if d (strcat d "\\Documents\\Brezly") (getvar "TEMPPREFIX")))

(defun br:failas () (strcat (br:kelias) "\\lisp_progresas.txt"))

(defun br:skaityti (/ f l r)
  (setq r nil)
  (if (setq f (open (br:failas) "r"))
    (progn
      (while (setq l (read-line f))
        (if (/= l "") (setq r (cons l r))))
      (close f)))
  r)

(defun br:rasyti (lst / f)
  (if vl-mkdir (vl-mkdir (br:kelias)))
  (if (setq f (open (br:failas) "w"))
    (progn (foreach x lst (write-line x f)) (close f))
    (princ "\nBrezly: nepavyko issaugoti progreso.")))

(defun br:atlikta-p (u) (member (car u) (br:skaityti)))

(defun br:pazymeti (u / l)
  (setq l (br:skaityti))
  (if (not (member (car u) l))
    (br:rasyti (cons (car u) l))))

(defun br:xp (/ l s)
  (setq l (br:skaityti) s 0)
  (foreach u *br:uzd* (if (member (car u) l) (setq s (+ s (nth 5 u)))))
  s)

(defun br:pirma-neatlikta (/ l i r)
  (setq l (br:skaityti) i 0 r nil)
  (foreach u *br:uzd*
    (if (and (null r) (not (member (car u) l))) (setq r i))
    (setq i (1+ i)))
  (if r r 0))

(if (null *br:cur*) (setq *br:cur* (br:pirma-neatlikta)))

;;; ---------- brezinio analize ----------

(defun br:ignoruoti-p (sl)
  (wcmatch (strcase sl) "REMELIS,BR_*,DEFPOINTS"))

(defun br:ne-geometrija-p (sl)
  (wcmatch (strcase sl) "ASYS,MATMENYS,*DIM*"))

(defun br:prideti (k n / p)
  (if (setq p (assoc k *br:sk*))
    (setq *br:sk* (subst (cons k (+ (cdr p) n)) p *br:sk*))
    (setq *br:sk* (cons (cons k n) *br:sk*))))

(defun br:sk (k / p) (if (setq p (assoc k *br:sk*)) (cdr p) 0))

(defun br:taskas (pt)
  (if *br:bmin*
    (setq *br:bmin* (list (min (car *br:bmin*) (car pt)) (min (cadr *br:bmin*) (cadr pt)))
          *br:bmax* (list (max (car *br:bmax*) (car pt)) (max (cadr *br:bmax*) (cadr pt))))
    (setq *br:bmin* (list (car pt) (cadr pt))
          *br:bmax* (list (car pt) (cadr pt)))))

(defun br:analizuoti (/ ss i e d tp sl n b v p)
  (setq *br:sk* nil *br:r* nil *br:bmin* nil *br:bmax* nil *br:solid* nil)
  (if (setq ss (ssget "_X" '((410 . "Model"))))
    (progn
      (setq i 0)
      (repeat (sslength ss)
        (setq e  (ssname ss i)
              i  (1+ i)
              d  (entget e)
              tp (cdr (assoc 0 d))
              sl (cdr (assoc 8 d)))
        (if (not (br:ignoruoti-p sl))
          (cond
            ((= tp "CIRCLE")
             (br:prideti "CIRCLE" 1)
             (setq *br:r* (cons (cdr (assoc 40 d)) *br:r*)))
            ((= tp "LINE")
             (br:prideti "LINE" 1)
             (if (not (br:ne-geometrija-p sl))
               (progn (br:taskas (cdr (assoc 10 d)))
                      (br:taskas (cdr (assoc 11 d))))))
            ((= tp "LWPOLYLINE")
             (setq n 0 b 0)
             (foreach p d
               (cond
                 ((= (car p) 10)
                  (setq n (1+ n))
                  (if (not (br:ne-geometrija-p sl)) (br:taskas (cdr p))))
                 ((and (= (car p) 42) (> (abs (cdr p)) 1e-9))
                  (setq b (1+ b)))))
             (setq v (if (= 1 (logand 1 (cdr (assoc 70 d)))) n (1- n)))
             (if (< v 0) (setq v 0))
             (if (> b v) (setq b v))
             (br:prideti "ARC" b)
             (br:prideti "LINE" (- v b)))
            ((= tp "3DSOLID")
             (br:prideti "3DSOLID" 1)
             (setq *br:solid* (cons e *br:solid*)))
            (t (br:prideti tp 1)))))))
  (princ))

(defun br:kiek-r (r / n)
  (setq n 0)
  (foreach x *br:r* (if (< (abs (- x r)) 0.05) (setq n (1+ n))))
  n)

;;; Grazina sumine turi arba nil, jei ActiveX nepasiekiamas (pvz. AutoCAD LT)
(defun br:turis (/ s v ok)
  (if vl-load-com (vl-load-com))
  (if (and vlax-ename->vla-object vl-catch-all-apply)
    (progn
      (setq s 0.0 ok T)
      (foreach e *br:solid*
        (setq v (vl-catch-all-apply 'vla-get-volume
                                    (list (vlax-ename->vla-object e))))
        (if (vl-catch-all-error-p v) (setq ok nil) (setq s (+ s v))))
      (if ok s nil))
    nil))

(defun br:tipo-vardas (tp)
  (cond ((= tp "LINE") "atkarpu (LINE / polilinijos tiesiu daliu)")
        ((= tp "ARC") "lanku (ARC / FILLET)")
        ((= tp "HATCH") "bruksniavimu (HATCH)")
        ((= tp "ELLIPSE") "elipsiu / izoapskritimu (ELLIPSE)")
        ((= tp "INSERT") "iterptu bloku (INSERT)")
        ((= tp "3DSOLID") "3D kunu (3DSOLID)")
        (t tp)))

;;; Grazina (priimta-p geri klaidos pastabos)
(defun br:tikrinti (u / geri klaidos pastabos n w h v tp)
  (br:analizuoti)
  (setq geri nil klaidos nil pastabos nil)
  (foreach tr (nth 9 u)
    (cond
      ((= (car tr) "R")
       (setq n (br:kiek-r (cadr tr)))
       (if (>= n (caddr tr))
         (setq geri (cons (strcat (itoa (caddr tr)) " x apskritimas R" (br:fmt (cadr tr))) geri))
         (setq klaidos
           (cons (strcat "Truksta apskritimu R" (br:fmt (cadr tr))
                         ": rasta " (itoa n) " is " (itoa (caddr tr))
                         (if (> (br:kiek-r (* 2.0 (cadr tr))) 0)
                           (strcat ". Rasta R" (br:fmt (* 2.0 (cadr tr)))
                                   " - ar ne skersmuo ivestas vietoj spindulio?")
                           ""))
                 klaidos))))
      ((= (car tr) "T")
       (setq tp (cadr tr) n (br:sk tp))
       (if (>= n (caddr tr))
         (setq geri (cons (strcat (itoa n) " " (br:tipo-vardas tp)) geri))
         (setq klaidos
           (cons (strcat "Per mazai " (br:tipo-vardas tp) ": " (itoa n)
                         ", reikia bent " (itoa (caddr tr)))
                 klaidos))))
      ((= (car tr) "DYDIS")
       (if *br:bmin*
         (progn
           (setq w (- (car *br:bmax*) (car *br:bmin*))
                 h (- (cadr *br:bmax*) (cadr *br:bmin*)))
           (if (and (< (abs (- w (cadr tr))) 0.5) (< (abs (- h (caddr tr))) 0.5))
             (setq geri (cons (strcat "Konturo dydis " (br:fmt w) " x " (br:fmt h)) geri))
             (setq klaidos
               (cons (strcat "Konturo dydis " (br:fmt w) " x " (br:fmt h)
                             ", reikia " (br:fmt (cadr tr)) " x " (br:fmt (caddr tr))
                             " (asis laikyk sluoksnyje ASYS)")
                     klaidos))))
         (setq klaidos (cons "Nerastas konturas (linijos arba polilinija)" klaidos))))
      ((= (car tr) "TURIS")
       (if *br:solid*
         (if (setq v (br:turis))
           (if (<= (abs (- v (cadr tr))) (* (cadr tr) (/ (caddr tr) 100.0)))
             (setq geri (cons (strcat "Turis " (br:fmt v) " mm3") geri))
             (setq klaidos
               (cons (strcat "Turis " (br:fmt v) " mm3, turi buti apie "
                             (br:fmt (cadr tr)) " mm3. Ar atlikai UNION ir SUBTRACT?")
                     klaidos)))
           (setq pastabos
             (cons (strcat "Turio patikrinti nepavyko (tik pilname AutoCAD). "
                           "Patikrink MASSPROP: apie " (br:fmt (cadr tr)) " mm3")
                   pastabos)))))))
  (list (null klaidos) (reverse geri) (reverse klaidos) (reverse pastabos)))

;;; Atlieka tikrinima, isspausdina ir grazina eilutes langui
(defun br:atlikti-tikrinima (/ u r eil buvo)
  (setq u (br:u *br:cur*)
        buvo (br:atlikta-p u)
        r (br:tikrinti u)
        eil nil)
  (princ (strcat "\n--- Brezly: " (nth 1 u) " ---"))
  (if (car r)
    (progn
      (if (not buvo) (br:pazymeti u))
      (setq eil (list (if buvo
                        "PRIIMTA (jau buvo atlikta anksciau)"
                        (strcat "PRIIMTA!  +" (itoa (nth 5 u)) " XP")))))
    (setq eil (list "TAISYTI - ziurek zemiau:")))
  (foreach x (caddr r) (setq eil (cons (strcat "  x " x) eil)))
  (foreach x (cadddr r) (setq eil (cons (strcat "  ! " x) eil)))
  (foreach x (cadr r) (setq eil (cons (strcat "  v " x) eil)))
  (setq eil (reverse eil))
  (foreach x eil (princ (strcat "\n" x)))
  (princ (strcat "\nIs viso: " (itoa (br:xp)) " XP"))
  (setq *br:rez* eil)
  (if (car r) "Priimta" "Reikia taisyti"))

;;; ---------- lapas ----------

(defun br:sluoksnis (nm sp)
  (if (not (tblsearch "LAYER" nm))
    (entmake (list '(0 . "LAYER")
                   '(100 . "AcDbSymbolTableRecord")
                   '(100 . "AcDbLayerTableRecord")
                   (cons 2 nm) '(70 . 0) (cons 62 sp) '(6 . "Continuous")))))

(defun br:staciak (x1 y1 x2 y2 sl)
  (entmake (list '(0 . "LWPOLYLINE") '(100 . "AcDbEntity") (cons 8 sl)
                 '(100 . "AcDbPolyline") '(90 . 4) '(70 . 1)
                 (list 10 x1 y1) (list 10 x2 y1) (list 10 x2 y2) (list 10 x1 y2))))

(defun br:linija (x1 y1 x2 y2 sl)
  (entmake (list '(0 . "LINE") (cons 8 sl)
                 (list 10 x1 y1 0.0) (list 11 x2 y2 0.0))))

(defun br:tekstas (x y h s sl)
  (entmake (list '(0 . "TEXT") (cons 8 sl)
                 (list 10 x y 0.0) (cons 40 h) (cons 1 s))))

(defun br:lapas (/ u a4 W x0 x1 ss i data)
  (setq u (br:u *br:cur*)
        a4 (= (nth 2 u) "A4")
        W  (if a4 210.0 420.0)
        x1 (- W 5.0)
        x0 (- x1 185.0))
  (br:sluoksnis "REMELIS" 8)
  (br:sluoksnis "KONTURAS" 7)
  (br:sluoksnis "ASYS" 1)
  (br:sluoksnis "MATMENYS" 4)
  (br:sluoksnis "NEMATOMOS" 3)
  (br:sluoksnis "BRUKSNIAVIMAS" 9)
  ;; seno remelio salinimas
  (if (setq ss (ssget "_X" '((8 . "REMELIS"))))
    (progn (setq i 0)
           (repeat (sslength ss) (entdel (ssname ss i)) (setq i (1+ i)))))
  (setq data (menucmd "M=$(edtime,$(getvar,date),YYYY-MO-DD)"))
  ;; lapas ir remelis
  (br:staciak 0.0 0.0 W 297.0 "REMELIS")
  (br:staciak 20.0 5.0 x1 292.0 "REMELIS")
  ;; spaudas 185 x 40
  (br:staciak x0 5.0 x1 45.0 "REMELIS")
  (br:linija x0 25.0 x1 25.0 "REMELIS")
  (br:linija (+ x0 60.0) 5.0 (+ x0 60.0) 45.0 "REMELIS")
  (br:linija (+ x0 135.0) 5.0 (+ x0 135.0) 25.0 "REMELIS")
  (br:tekstas (+ x0 4.0) 33.0 5.0 "BREZLY" "REMELIS")
  (br:tekstas (+ x0 4.0) 27.0 2.5 "Praktikos uzduotis" "REMELIS")
  (br:tekstas (+ x0 64.0) 32.0 5.0
              (strcat (itoa (1+ *br:cur*)) ". " (strcase (nth 1 u))) "REMELIS")
  (br:tekstas (+ x0 4.0) 16.0 3.0 "Atliko:" "REMELIS")
  (br:tekstas (+ x0 4.0) 8.0 2.5 data "REMELIS")
  (br:tekstas (+ x0 64.0) 16.0 3.0
              (strcat (nth 2 u) "   " (nth 3 u) "   M 1:1") "REMELIS")
  (br:tekstas (+ x0 139.0) 16.0 3.0 (car u) "REMELIS")
  (setvar "CLAYER" "KONTURAS")
  (command "_.ZOOM" "_E")
  (princ (strcat "\nBrezly: lapas " (nth 2 u) " paruostas. Braizyk remelio viduje, sluoksnis KONTURAS."))
  (princ))

;;; ---------- langas (DCL) ----------

(defun br:dcl (/ fn f)
  (setq fn (strcat (getvar "TEMPPREFIX") "brezly.dcl"))
  (if (setq f (open fn "w"))
    (progn
      (foreach l
        (list
         "brezly : dialog {"
         "  key = \"ttl\"; label = \"Brezly\";"
         "  : row {"
         "    : list_box { key = \"uzd\"; label = \"Uzduotys\"; width = 32; height = 18; }"
         "    : list_box { key = \"info\"; label = \"Aprasas\"; width = 66; height = 18; }"
         "  }"
         "  : text { key = \"msg\"; width = 100; }"
         "  : row {"
         "    : button { key = \"lapas\"; label = \"Paruosti lapa\"; width = 18; }"
         "    : button { key = \"tikr\"; label = \"Patikrinti\"; width = 18; is_default = true; }"
         "    : button { key = \"cancel\"; label = \"Uzdaryti\"; width = 14; is_cancel = true; }"
         "  }"
         "}")
        (write-line l f))
      (close f)
      fn)
    nil))

(defun br:info-eilutes (/ u e n)
  (setq u (br:u *br:cur*) n 1)
  (setq e (append
            (if *br:rez* (append *br:rez* (list "")) nil)
            (list (strcat (itoa (1+ *br:cur*)) ". " (nth 1 u)
                          "   " (nth 2 u) " " (nth 3 u)
                          "   ~" (itoa (nth 4 u)) " min   " (itoa (nth 5 u)) " XP"
                          (if (br:atlikta-p u) "   [ATLIKTA]" ""))
                  "")
            (br:skaidyti (nth 6 u) 64)
            (list "" (strcat "Komandos: " (nth 7 u)) "" "Zingsniai:")))
  (foreach z (nth 8 u)
    (setq e (append e (br:skaidyti (strcat (itoa n) ". " z) 64)) n (1+ n)))
  e)

(defun br:pildyti-info ()
  (start_list "info")
  (foreach x (br:info-eilutes) (add_list x))
  (end_list))

(defun br:pildyti-sarasa (/ l i)
  (setq l (br:skaityti) i 1)
  (start_list "uzd")
  (foreach u *br:uzd*
    (add_list (strcat (if (member (car u) l) "[v] " "[  ] ")
                      (itoa i) ". " (nth 1 u) "  (" (nth 2 u) ")"))
    (setq i (1+ i)))
  (end_list)
  (set_tile "uzd" (itoa *br:cur*)))

(defun br:pasirinkta (v)
  (setq *br:cur* (atoi v) *br:rez* nil)
  (br:pildyti-info)
  (set_tile "msg" ""))

(defun c:BREZLY (/ fn id kodas msg)
  (setq fn (br:dcl))
  (if (or (null fn) (< (setq id (load_dialog fn)) 0))
    (progn (princ "\nBrezly: nepavyko atidaryti lango. Naudok TIKRINK ir BRLAPAS.") (exit)))
  (setq kodas 9 msg "Pasirink uzduoti, spausk \"Paruosti lapa\", nubraizyk ir spausk \"Patikrinti\".")
  (while (/= kodas 0)
    (if (not (new_dialog "brezly" id)) (exit))
    (set_tile "ttl" (strcat "Brezly " *br:ver* " - AutoCAD praktika     " (itoa (br:xp)) " XP"))
    (br:pildyti-sarasa)
    (br:pildyti-info)
    (set_tile "msg" msg)
    (action_tile "uzd" "(br:pasirinkta $value)")
    (action_tile "lapas" "(done_dialog 2)")
    (action_tile "tikr" "(done_dialog 3)")
    (action_tile "cancel" "(done_dialog 0)")
    (setq kodas (start_dialog))
    (cond
      ((= kodas 2)
       (br:lapas)
       (setq *br:rez* nil
             msg "Lapas paruostas. Uzdaryk langa ir braizyk, po to vel BREZLY -> Patikrinti.")
       (setq kodas 0))
      ((= kodas 3)
       (setq msg (br:atlikti-tikrinima)))))
  (unload_dialog id)
  (princ))

(defun c:TIKRINK () (br:atlikti-tikrinima) (princ))
(defun c:BRLAPAS () (br:lapas))

(princ (strcat "\nBrezly " *br:ver* " ikeltas. Komandos: BREZLY - praktikos langas, "
               "BRLAPAS - paruosti lapa, TIKRINK - patikrinti."))
(princ)
