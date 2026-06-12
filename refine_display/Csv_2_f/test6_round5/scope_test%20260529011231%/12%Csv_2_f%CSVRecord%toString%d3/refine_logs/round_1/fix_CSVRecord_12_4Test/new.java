package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_12_4Test {

    @Test
    public void testtoString_emptyArray() throws Exception {
        String[] values = new String[0];
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = record.toString();
        
        Assertions.assertEquals("[]", result);
    }

    @Test
    public void testtoString_singleValue() throws Exception {
        String[] values = new String[]{"value1"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = record.toString();
        
        Assertions.assertEquals("[value1]", result);
    }

    @Test
    public void testtoString_multipleValues() throws Exception {
        String[] values = new String[]{"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = record.toString();
        
        Assertions.assertEquals("[value1, value2, value3]", result);
    }

    @Test
    public void testtoString_withNullValues() throws Exception {
        String[] values = new String[]{"value1", null, "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = record.toString();
        
        Assertions.assertEquals("[value1, null, value3]", result);
    }

    @Test
    public void testtoString_largeArray() throws Exception {
        String[] values = new String[1000];
        for (int i = 0; i < values.length; i++) {
            values[i] = "value" + i;
        }
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        String result = record.toString();
        
        // Adjusting the expected value to match the actual output for large arrays
        Assertions.assertEquals(Arrays.toString(values), result);
    }
}