package org.apache.commons.csv;

import java.io.BufferedReader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;

class ExtendedBufferedReader_2_2Test {

    @Test
    void testRead_newLine() throws Exception {
        String input = "First line\nSecond line";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        int firstChar = reader.read();
        int secondChar = reader.read();
        
        Assertions.assertEquals('F', firstChar);
        Assertions.assertEquals('i', secondChar);
        
        // Read until the new line
        while (reader.read() != '\n') {}
        
        // Now we check if the lineCounter has increased
        Assertions.assertEquals(1, invokeGetLineNumber(reader));
    }

    @Test
    void testRead_carriageReturn() throws Exception {
        String input = "First line\rSecond line";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);
        
        // Read until the carriage return
        while (reader.read() != '\r') {}
        
        // Check if lineCounter has increased
        Assertions.assertEquals(1, invokeGetLineNumber(reader));
    }

    @Test
    void testRead_noNewLine() throws Exception {
        String input = "First line";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);
        
        while (reader.read() != -1) {}
        
        // Check if lineCounter remains zero
        Assertions.assertEquals(0, invokeGetLineNumber(reader));
    }

    @Test
    void testRead_endOfStream() throws Exception {
        String input = "";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);
        
        int result = reader.read();
        
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
        Assertions.assertEquals(0, invokeGetLineNumber(reader)); // Ensure lineCounter is also zero
    }

    @Test
    void testRead_lineBreaks() throws Exception {
        String input = "Line1\rLine2\nLine3\r\nLine4";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);

        while (reader.read() != -1) {}
        
        // Check if lineCounter is 4 after reading all lines
        Assertions.assertEquals(4, invokeGetLineNumber(reader));
    }

    @Test
    void testReadAgain() throws Exception {
        String input = "Test read again\n";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);
        
        reader.read(); // Read first character
        int result = reader.readAgain(); // Assuming readAgain reads the next character
        
        Assertions.assertEquals('e', result); // Assuming the second character is 'e'
    }

    @Test
    void testReadLine() throws Exception {
        String input = "First line\nSecond line";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);
        
        String firstLine = reader.readLine();
        Assertions.assertEquals("First line", firstLine);
        Assertions.assertEquals(1, invokeGetLineNumber(reader)); // Check lineCounter
    }

    @Test
    void testLookAhead() throws Exception {
        String input = "Look ahead test\n";
        Reader stringReader = new StringReader(input);
        ExtendedBufferedReader reader = new ExtendedBufferedReader(stringReader);
        
        int lookAheadChar = reader.lookAhead(); // Assuming lookAhead reads the next character without advancing
        Assertions.assertEquals('L', lookAheadChar);
        
        // Ensure lineCounter remains unchanged
        Assertions.assertEquals(0, invokeGetLineNumber(reader));
    }

    private int invokeGetLineNumber(ExtendedBufferedReader reader) throws Exception {
        var method = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        method.setAccessible(true);
        return (int) method.invoke(reader);
    }
}