package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.lang.reflect.Method;

class ExtendedBufferedReader_1_4Test {

    @Test
    void testExtendedBufferedReader_normalCase() throws Exception {
        String input = "Hello, World!\nThis is a test.";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader extendedBufferedReader = new ExtendedBufferedReader(reader);
        
        String line1 = extendedBufferedReader.readLine();
        Assertions.assertEquals("Hello, World!", line1);
        
        String line2 = extendedBufferedReader.readLine();
        Assertions.assertEquals("This is a test.", line2);
    }

    @Test
    void testRead_emptyStream() throws Exception {
        Reader reader = new StringReader("");
        ExtendedBufferedReader extendedBufferedReader = new ExtendedBufferedReader(reader);
        
        String line = extendedBufferedReader.readLine();
        Assertions.assertEquals(null, line);
    }

    @Test
    void testRead_singleCharacter() throws Exception {
        Reader reader = new StringReader("A");
        ExtendedBufferedReader extendedBufferedReader = new ExtendedBufferedReader(reader);
        
        int charRead = extendedBufferedReader.read();
        Assertions.assertEquals('A', charRead);
        
        charRead = extendedBufferedReader.read();
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, charRead);
    }

    @Test
    void testReadLine_withNewLine() throws Exception {
        String input = "First Line\nSecond Line\n";
        Reader reader = new StringReader(input);
        ExtendedBufferedReader extendedBufferedReader = new ExtendedBufferedReader(reader);
        
        String firstLine = extendedBufferedReader.readLine();
        Assertions.assertEquals("First Line", firstLine);
        
        String secondLine = extendedBufferedReader.readLine();
        Assertions.assertEquals("Second Line", secondLine);
    }

    @Test
    void testLookAhead() throws Exception {
        Reader reader = new StringReader("Sample text");
        ExtendedBufferedReader extendedBufferedReader = new ExtendedBufferedReader(reader);
        
        Method lookAheadMethod = ExtendedBufferedReader.class.getDeclaredMethod("lookAhead");
        lookAheadMethod.setAccessible(true);
        
        int lookAheadChar = (int) lookAheadMethod.invoke(extendedBufferedReader);
        Assertions.assertEquals('S', lookAheadChar);
    }

    @Test
    void testGetLineNumber() throws Exception {
        Reader reader = new StringReader("Line 1\nLine 2");
        ExtendedBufferedReader extendedBufferedReader = new ExtendedBufferedReader(reader);
        
        Method getLineNumberMethod = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        getLineNumberMethod.setAccessible(true);
        
        extendedBufferedReader.readLine(); // Read first line
        int lineNumber = (int) getLineNumberMethod.invoke(extendedBufferedReader);
        Assertions.assertEquals(1, lineNumber);
        
        extendedBufferedReader.readLine(); // Read second line
        lineNumber = (int) getLineNumberMethod.invoke(extendedBufferedReader);
        Assertions.assertEquals(2, lineNumber);
    }
}