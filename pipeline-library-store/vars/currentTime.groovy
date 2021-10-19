def call(){
   return(new Date().format("yyyy/MM/dd.HH:mm:ss", TimeZone.getTimeZone('UTC-05:00')))
}