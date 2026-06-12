package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Collections;
import java.util.Iterator;
import java.util.Map;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

public class CSVRecord_7_3Test {

    @Test
    public void testiterator_normalCase() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1);

        Iterator<String> iterator = csvRecord.iterator();
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value1", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value2", iterator.next());
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("value3", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testiterator_emptyValues() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1);

        Iterator<String> iterator = csvRecord.iterator();
        Assertions.assertFalse(iterator.hasNext());
    }

    @Test
    public void testiterator_singleValue() throws Exception {
        String[] values = {"singleValue"};
        Map<String, Integer> mapping = Collections.emptyMap();
        CSVRecord csvRecord = new CSVRecord(values, mapping, null, 1);

        Iterator<String> iterator = csvRecord.iterator();
        Assertions.assertTrue(iterator.hasNext());
        Assertions.assertEquals("singleValue", iterator.next());
        Assertions.assertFalse(iterator.hasNext());
    }
}