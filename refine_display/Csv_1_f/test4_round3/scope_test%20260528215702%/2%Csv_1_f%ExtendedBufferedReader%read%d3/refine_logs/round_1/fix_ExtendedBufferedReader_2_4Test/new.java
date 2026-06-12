package org.apache.commons.csv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.Reader;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.io.StringReader;
import java.lang.reflect.Method;

class ExtendedBufferedReader_2_4Test {

    @Test
    void testRead_normalCase() throws Exception {
        String input = "Hello\nWorld";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        int firstChar = reader.read();
        Assertions.assertEquals('H', firstChar);
        
        int secondChar = reader.read();
        Assertions.assertEquals('e', secondChar);
        
        int lineBreak = reader.read();
        Assertions.assertEquals('l', lineBreak);
        
        int lineCounter = invokeGetLineNumber(reader);
        Assertions.assertEquals(0, lineCounter); // No line break yet

        // Read until line break
        reader.read(); // 'l'
        reader.read(); // 'o'
        int newLine = reader.read(); // '\n'
        Assertions.assertEquals('\n', newLine);
        
        lineCounter = invokeGetLineNumber(reader);
        Assertions.assertEquals(1, lineCounter); // Line break occurred
    }

    @Test
    void testRead_lineBreaks() throws Exception {
        String input = "Line1\r\nLine2\rLine3\n";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        reader.read(); // 'L'
        reader.read(); // 'i'
        reader.read(); // 'n'
        reader.read(); // 'e'
        reader.read(); // '1'
        int firstLineBreak = reader.read(); // '\r'
        Assertions.assertEquals('\r', firstLineBreak);
        
        int lineCounter = invokeGetLineNumber(reader);
        Assertions.assertEquals(0, lineCounter); // Line break not counted yet

        int secondLineBreak = reader.read(); // '\n'
        Assertions.assertEquals('\n', secondLineBreak);
        
        lineCounter = invokeGetLineNumber(reader);
        Assertions.assertEquals(1, lineCounter); // First line counted

        // Read second line
        reader.read(); // 'L'
        reader.read(); // 'i'
        reader.read(); // 'n'
        reader.read(); // 'e'
        reader.read(); // '2'
        int secondLineEnd = reader.read(); // '\r'
        Assertions.assertEquals('\r', secondLineEnd);
        
        lineCounter = invokeGetLineNumber(reader);
        Assertions.assertEquals(1, lineCounter); // Still only one line counted

        int thirdLineBreak = reader.read(); // '\n'
        Assertions.assertEquals('\n', thirdLineBreak);
        
        lineCounter = invokeGetLineNumber(reader);
        Assertions.assertEquals(2, lineCounter); // Second line counted

        // Read third line
        reader.read(); // 'L'
        reader.read(); // 'i'
        reader.read(); // 'n'
        reader.read(); // 'e'
        reader.read(); // '3'
        int endOfStream = reader.read(); // END_OF_STREAM
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, endOfStream);
        
        lineCounter = invokeGetLineNumber(reader);
        Assertions.assertEquals(3, lineCounter); // Third line counted
    }

    @Test
    void testRead_endOfStream() throws Exception {
        String input = "";
        ExtendedBufferedReader reader = new ExtendedBufferedReader(new StringReader(input));
        
        int result = reader.read();
        Assertions.assertEquals(ExtendedBufferedReader.END_OF_STREAM, result);
        
        int lineCounter = invokeGetLineNumber(reader);
        Assertions.assertEquals(0, lineCounter); // No lines read
    }

    private int invokeGetLineNumber(ExtendedBufferedReader reader) throws Exception {
        Method method = ExtendedBufferedReader.class.getDeclaredMethod("getLineNumber");
        method.setAccessible(true);
        return (int) method.invoke(reader);
    }
}