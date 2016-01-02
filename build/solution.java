import java.io.*;

public class solution {
  public static void main(String[] args) {
    try{
      BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));
      System.out.println("T");
      String[] data = reader.readLine().split(":");
      System.out.println(data[0] + ":" + data[2]);
    } catch(IOException e) {
    }
  }
}
