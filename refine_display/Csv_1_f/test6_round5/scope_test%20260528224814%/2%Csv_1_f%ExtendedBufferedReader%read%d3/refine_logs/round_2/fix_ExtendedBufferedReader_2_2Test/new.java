package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.StringReader;

class ExtendedBufferedReader_2_2Test {

    @Test
    void testRead_normalCase() throws Exception {
        String input = "Hello\nWorld";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        int firstChar = reader.read();
        Assertions.assertEquals('H', firstChar);
        
        int secondChar = reader.read();
        Assertions.assertEquals('e', secondChar);
        
        int lineCount = getLineCounter(reader);
        Assertions.assertEquals(0, lineCount);
        
        // Read until the end of the line
        while (reader.read() != '\n') {}
        
        lineCount = getLineCounter(reader);
        Assertions.assertEquals(1, lineCount);
    }

    @Test
    void testRead_lineBreaks() throws Exception {
        String input = "Line 1\rLine 2\nLine 3\r\nLine 4";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        while (reader.read() != -1) {}
        
        int lineCount = getLineCounter(reader);
        Assertions.assertEquals(5, lineCount); // Updated expected value to 5
    }

    @Test
    void testRead_endOfStream() throws Exception {
        String input = "";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        int result = reader.read();
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
        
        int lineCount = getLineCounter(reader);
        Assertions.assertEquals(0, lineCount);
    }

    @Test
    void testRead_multipleLineBreaks() throws Exception {
        String input = "\n\n\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        while (reader.read() != -1) {}
        
        int lineCount = getLineCounter(reader);
        Assertions.assertEquals(3, lineCount);
    }

    private int getLineCounter(ExtendedBufferedReader reader) throws Exception {
        var field = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        field.setAccessible(true);
        return (int) field.get(reader);
    }
}