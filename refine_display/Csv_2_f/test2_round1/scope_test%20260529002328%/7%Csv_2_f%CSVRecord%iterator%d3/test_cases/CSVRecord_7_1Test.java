package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Collections;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_7_1Test {

    @Test
    public void testiterator_normalCase() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Iterator<String> iterator = record.iterator();
        
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value1", iterator.next());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertEquals("value3", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testiterator_emptyArray() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Iterator<String> iterator = record.iterator();
        
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testiterator_singleElement() throws Exception {
        String[] values = {"singleValue"};
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Iterator<String> iterator = record.iterator();
        
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("singleValue", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testiterator_multipleSpaces() throws Exception {
        String[] values = {"   ", "value2", "   "};
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Iterator<String> iterator = record.iterator();
        
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("   ", iterator.next());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertEquals("   ", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testiterator_largeInput() throws Exception {
        String[] values = new String[1000];
        Arrays.fill(values, "value");
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Iterator<String> iterator = record.iterator();
        
        for (int i = 0; i < values.length; i++) {
            Assertions.assertTrue(iterator.hasNext());
            Assertions.assertEquals("value", iterator.next());
        }
        Assertions.assertFalse(iterator.hasNext());
    }
}