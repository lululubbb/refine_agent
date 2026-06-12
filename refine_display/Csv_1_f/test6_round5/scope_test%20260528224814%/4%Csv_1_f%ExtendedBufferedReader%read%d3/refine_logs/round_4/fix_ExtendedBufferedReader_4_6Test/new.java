package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.StringReader;
import java.lang.reflect.Field;

class ExtendedBufferedReader_4_6Test {

    @Test
    void testRead_normalCase() throws Exception {
        String input = "Hello\nWorld";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        char[] buffer = new char[10];
        int len = reader.read(buffer, 0, 10);
        
        Assertions.assertEquals(10, len);
        Assertions.assertEquals('H', buffer[0]);
        
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        Assertions.assertEquals(1, lineCounterField.get(reader));
    }

    @Test
    void testRead_emptyBuffer() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Test"));
        char[] buffer = new char[10];
        int len = reader.read(buffer, 0, 0);
        
        Assertions.assertEquals(0, len);
        Assertions.assertEquals('\0', buffer[0]); // Check that buffer remains unchanged
    }

    @Test
    void testRead_endOfStream() throws Exception {
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader("Test"));
        char[] buffer = new char[10];
        reader.read(buffer, 0, 4); // Read the whole input
        int len = reader.read(buffer, 0, 10); // Read again
        
        Assertions.assertEquals(-1, len);
        
        Field lastCharField = ExtendedBufferedReader.class.getDeclaredField("lastChar");
        lastCharField.setAccessible(true);
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, lastCharField.get(reader));
    }

    @Test
    void testRead_lineBreaks() throws Exception {
        String input = "Line1\rLine2\nLine3\r\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        char[] buffer = new char[20];
        int len = reader.read(buffer, 0, 20);
        
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        Assertions.assertEquals(3, lineCounterField.get(reader)); // Adjusted expected value to 3
        Assertions.assertArrayEquals("Line1\rLine2\nLine3\r\n".toCharArray(), buffer); // Check buffer content
    }
    
    @Test
    void testRead_noNewLine() throws Exception {
        String input = "NoNewLine";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        char[] buffer = new char[10];
        int len = reader.read(buffer, 0, 10);
        
        Assertions.assertEquals(9, len);
        Assertions.assertEquals("NoNewLine".toCharArray()[0], buffer[0]);
        
        Field lineCounterField = ExtendedBufferedReader.class.getDeclaredField("lineCounter");
        lineCounterField.setAccessible(true);
        Assertions.assertEquals(0, lineCounterField.get(reader));
    }
}