# Physiography Tool

Questo tool produrrà la fisiografia direttamente dentro il layer dedicato del vostro production .gdb e compilerà automaticamente tutti i campi dell'attribute table. Inoltre, contiene un algoritmo di "pulizia" che elimina automaticamente tutte le features più piccole che di solito vanno tolte a mano. Quindi non ci sarà più bisogno di processare preventivamente il DEM, produrre lo shapefile di fisiografia, compilare i campi e fare il load nel gdb.
Qui una breve descrizione dei parametri da compilare (con screen allegato sotto):

### Parameters

DEM file: inserite il percorso del DEM (potete anche trascinare il DEM direttamente dalla TOC come al solito)
DEM product: è un menù a tendina dove sono riportati i principali DEM utilizzati. Questo parametro serve per compilare automaticamente il campo "origin source identifier". Se il DEM che state utilizzando non è fra quelli elencati nel menù, selezionando l'opzione "None in this list" (come nello screen) comparirà un campo dove inserire il codice che volete usare
Geodatabase: inserite il .gdb di produzione
Buffer distance: potete selezionare un buffer così da produrre una fisiografia che va anche oltre la AOI (l'unità di misura è in metri)
Contour lines interval: selezionate l'intervallo delle contour lines. Più è basso, più la fisiografia apparirà "fitta" (l'unità di misura è in metri)
Threshold length: è un parametro usato dall'algoritmo per elimanre le features più piccole. Più è alto il suo valore e più grandi saranno le features che verranno eliminate. In generale consiglio di usare l'MMU (unità di misura sempre in metri).
