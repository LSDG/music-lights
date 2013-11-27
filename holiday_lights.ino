//variables to handle incomming serial communication
String Command; // String input from Command prompt
char inByte; // Byte input from Command prompt
boolean CHstate = 1;


//variables to handle light channels 
const int PINCOUNT = 32;           // the number of pins (i.e. the length of the array)
byte  ledPins[] = { 
  22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53 };   // an array of pin numbers to which LEDs are attached
boolean channelstate[]={
  1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1 };

//delay fo mechanical relays, mechanical relays should not be switched faster than 5 times a second
const int DelayTimer = 200; 




void setup() {
//set all pins used to output, and set them immediately low, reduces but doesn't eliminate unintended behavior
  for (int thisPin = 0; thisPin < PINCOUNT; thisPin++)  {
    pinMode(ledPins[thisPin], OUTPUT); 
    digitalWrite(ledPins[thisPin],LOW);
  }
  
  // Open serial communications 
  Serial.begin(115200);
  
  // send a test sequance

  for (int thisPin=0; thisPin < PINCOUNT; thisPin++)
  {
    Serial.print("testing channel ");
    Serial.println(thisPin);
    channelstate[thisPin] =0;
    SetChannels();
    delay(DelayTimer);
    channelstate[thisPin] =1;
    SetChannels();

  }

  
  // send an intro:
  Serial.println("LSDG Holiday Light controller ver 1.0 23 Oct 2013");
  Serial.println();  
}


//let's start this party!!!
void loop() {
//read in all commands
  if (Serial.available() > 0){
    GetSerial();
  }


//if you've got commands
  if (Command != 0)
  {
    ProcessCommand();
    SetChannels();
  }

}

void GetSerial()//just dumps the commands we care about into a string object. a string array would be more efficiance, but we have plenty of space in this guy
{
  while (Serial.available() > 0){
    inByte = Serial.read();
    // only keep if a 'p','P','s','S' or number, is recieved, all else ignored
    if ((inByte == 80 || inByte == 112) || (inByte ==83 || inByte ==115) || (inByte >= 48 &&     inByte <=57)) {
      Command.concat(inByte);
      Command.toUpperCase();
      delay(1); //found that if we didn't delay, it would try to partially read a command, confusing both the microcontroller and the idiot programming it
    }
  }
}


void SetChannels() //turns pins high or low according to values stored in arrays
{
  for (int thisPin=0; thisPin < PINCOUNT; thisPin++)
  {
    digitalWrite(ledPins[thisPin],channelstate[thisPin]); 

  }
  //delay(DelayTimer);
}



//takes string of commands, and sets values in channelstate accordingly
void ProcessCommand()
{
  //setup variables for command processing
  byte CommandByte;
  String OneChan;
  int pos;
  // process Command here!!!

  for (int Commandstep = 0;  Commandstep <Command.length(); Commandstep++)
  { 
    CommandByte=Command[Commandstep];
    if (CommandByte == 'P')
    { 
      OneChan = 0;
      Commandstep++;    
      CommandByte=Command[Commandstep];
      while( CommandByte  >= '0' && CommandByte  <='9')
      {
        OneChan.concat( Command[Commandstep]);
        Commandstep++;    
        CommandByte=Command[Commandstep];
      }
      if (CommandByte == 'S')
      {
        Commandstep++;
        CommandByte = Command[Commandstep];
        CHstate =1;
        if (CommandByte == '0')
        {
          CHstate = 1;
        }
        else
        {
            CHstate = 0;
        }
        channelstate[OneChan.toInt()] =CHstate ;
      }
      else
      {
        break;
      }
    }
    else
    {
      break;
    }
    
  }

Command = 0;  
}
