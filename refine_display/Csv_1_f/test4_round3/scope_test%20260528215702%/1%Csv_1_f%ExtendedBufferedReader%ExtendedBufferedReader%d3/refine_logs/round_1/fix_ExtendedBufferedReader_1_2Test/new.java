package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.Method;

class ExtendedBufferedReader_1_2Test {

    @Test
    void testExtendedBufferedReader_normalCase() throws Exception {
        String input = "Line 1\nLine 2\n";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);
        
        String firstLine = ebr.readLine();
        Assertions.assertEquals("Line 1", firstLine);
        
        String secondLine = ebr.readLine();
        Assertions.assertEquals("Line 2", secondLine);
        
        String endLine = ebr.readLine();
        Assertions.assertNull(endLine);
    }

    @Test
    void testRead_emptyInput() throws Exception {
        String input = "";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);
        
        String line = ebr.readLine();
        Assertions.assertNull(line);
    }

    @Test
    void testRead_singleCharacter() throws Exception {
        String input = "A";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);
        
        int charRead = ebr.read();
        Assertions.assertEquals('A', charRead);
        
        charRead = ebr.read();
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, charRead);
    }

    @Test
    void testReadAgain() throws Exception {
        String input = "AB";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);
        
        Method readAgainMethod = ExtendedBufferedReader.class.getDeclaredMethod("readAgain");
        readAgainMethod.setAccessible(true);
        
        int result = (int) readAgainMethod.invoke(ebr);
        Assertions.assertNotEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    @Test
    void testLookAhead() throws Exception {
        String input = "Hello";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);
        
        Method lookAheadMethod = ExtendedBufferedReader.class.getDeclaredMethod("lookAhead");
        lookAheadMethod.setAccessible(true);
        
        int result = (int) lookAheadMethod.invoke(ebr);
        Assertions.assertNotEquals(ExtendedBufferedReader.END_OF_STREAM, result);
    }

    @Test
    void testGetLineNumber() throws Exception {
        String input = "Line 1\nLine 2\n";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);
        
        Method getLineNumberMethod = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        getLineNumberMethod.setAccessible(true);
        
        ebr.readLine(); // Read first line
        int lineNumber = (int) getLineNumberMethod.invoke(ebr);
        Assertions.assertEquals(1, lineNumber);
        
        ebr.readLine(); // Read second line
        lineNumber = (int) getLineNumberMethod.invoke(ebr);
        Assertions.assertEquals(2, lineNumber);
    }

    @Test
    void testReadWithBuffer() throws Exception {
        String input = "Buffered Read Test";
        char[] buffer = new char[10];
        Reader reader = new StringReader(input);
        ExtendedBufferedReader ebr = new ExtendedBufferedReader(reader);
        
        int charsRead = ebr.read(buffer, 0, buffer.length);
        Assertions.assertTrue(charsRead > 0);
        Assertions.assertEquals("Buffered Re", new String(buffer, 0, charsRead).trim());
    }
}