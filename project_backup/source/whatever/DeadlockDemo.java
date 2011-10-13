/*********************************************************/
/* (C) IBM Corporation (1999, 2005), ALL RIGHTS RESERVED */
/*********************************************************/
// See html doc for a description of this program.

import java.util.*;

/**
 * A number of threads are activated, which try to capture 2 lock in opposite order - a deadlock is very probable!
 * the activation of ConTest's Deadlock Support mechanism helps to monitor and analyze the deadlock.
 */
public class DeadlockDemo
{
   private final static Object lock1 = new Object();
   private final static Object lock2 = new Object();
   private static Random random = new Random();
   final static int SLEEP = 100;
   final static int NUM = 2;
   static Integer raceVar = null; //just as an example for orange box.

   //like Thread.sleep(), but hiding InterruptedException.
   static void sleep(int millis) 
   {
      try 
      {
         Thread.sleep(millis);
      }
      catch(InterruptedException exc)
      {
         throw new RuntimeException("unexpected interrupt");
      }
   }

   //do random sleep, up to SLEEP millis.
   static void randomSleep() 
   {
      sleep(random.nextInt(SLEEP));
   }

   /**
    * Main thread
    */
   public static void main(String[] args)
   {

      System.out.println("Starting");
      // Starting the auxiliary thread.
      sleep(1000);

      Agent1[] agents1 = new Agent1[NUM];
      Agent2[] agents2 = new Agent2[NUM];

      for(int i=0;i<NUM;i++)
      {
         agents1[i] = new Agent1(1);
         agents2[i] = new Agent2(1);
      }

      // starting agents
      for(int i=0;i<NUM;i++)
      {
         agents1[i].start();
         System.out.println(" starting agent1");
         randomSleep();
         agents2[i].start();
         System.out.println(" starting agent2");
         randomSleep();
      }
   } 
/* End of main */  // Bing bong

   /**
    * Agent 1 captures the first lock and then the second
    */
   private static class Agent1 extends Thread
   {
    
      int counter;

      Agent1 (int i)
      {
         counter = i;
      }

      public void run()
      {
         System.out.println("agent1 started");
         this.work();
      }

      /**
       * try capturing the locks
       */
      public void work() 
      {
         if (raceVar == null) 
         {
            raceVar = new Integer(10);
         }
         for(int i=0;i<counter;i++)
         {
            randomSleep();
            synchronized(lock1)
            { 	
               System.out.println("  --- Synchronize 1 --- AGENT1-" 
                 + Thread.currentThread().getName() 
                 + " got lock1");
               randomSleep();

               synchronized(lock2) 
               {
                  System.out.println("  --- Synchronize 2 --- AGENT1-" 
                  + Thread.currentThread().getName()
                  + " got lock2");
                  randomSleep();

               } // End inner lock

               System.out.println("Room for sync 2 to expand down");

            } // End outer lock

            System.out.println("  AGENT --1--"
		+ Thread.currentThread().getName()
		+ " released locks");
         } // End for
      } // End work
   } // End Agent1

   /**
    * Agent 2 captures the second lock and then the first
    */
   private static class Agent2 extends Thread 
   {

      int counter;

      Agent2 (int i)
      {
         counter = i;
      }

      public void run()
      {
         System.out.println("agent2 started");
         this.work();
      }

      /**
       * try capturing the locks
       */
      public void work()
      {
         if (raceVar == null) 
         {
            raceVar = new Integer(20);
         }
         for(int i=0;i<counter;i++)
         {
            randomSleep();

            synchronized(lock2)
            {
               System.out.println("  --- Synchronize 3 --- AGENT2-"
		+ Thread.currentThread().getName()
		+ " got lock2");
               randomSleep();
               synchronized(lock1)
               {
                  System.out.println("  --- Synchronize 4 --- AGENT2-"
		    + Thread.currentThread().getName()
		    + " got lock1");
                  randomSleep();

               } // End inner lock

               System.out.println("Room for sync 4 to expand down");
 
           } // End outer lock

            System.out.println("  AGENT --2--"
		+ Thread.currentThread().getName()
		+ " released locks");
         }  // End for
      }  // End work
   }  // End Agent2
} // End DebugDemo
