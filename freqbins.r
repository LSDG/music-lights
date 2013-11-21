freqbins <- function(filename) {

  results <- read.csv(filename, header = T, stringsAsFactors = F)

  #The last column seems to be all NAs. Thus, remove it from the data frame.
  results <- results[,-ncol(results)]
  results <- results[(rowSums(results) > 0),]

  results.mat <- as.matrix(results)

  #Normalize each row so that they individually sum to 1.
  mat.norm <- results.mat/rowSums(results.mat)
  results <- as.data.frame(mat.norm)
  rm(results.mat)
  rm(mat.norm)

  results.colmeans <- as.numeric(colMeans(results))

  #Prob represents a loudness-weighted probability
  bins.df <- data.frame(Start = 0, End = 0, Prob = 0)

  i = 1
  while(i <= 1000) {
  
    startbin <- i
  
    binsum <- 0
  
    while((binsum < 1/32) & (i <= 1000)) {
    
      binsum <- binsum+results.colmeans[i]
    
      i = i+1
    
    }
  
    endbin <- i
  
    bins.df <- rbind(bins.df, data.frame(Start = as.numeric(gsub('\\bX([0-9.]+)\\b\\.Hz', '\\1', names(results[max(startbin, 1)]))),
                                         End = as.numeric(gsub('\\bX([0-9.]+)\\b\\.Hz', '\\1', names(results[min(endbin, ncol(results))]))),
                                         Prob = binsum))
  
  }

  bins.df <- bins.df[-1,]
  
  return(bins.df)
  
}